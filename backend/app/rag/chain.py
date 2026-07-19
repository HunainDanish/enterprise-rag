import logging
import time
from collections import OrderedDict
from collections.abc import Sequence
from typing import Any, TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.core.llm import llm
from app.models.chat_log import ChatLog
from app.rag.prompts import RAG_PROMPT, RAG_PROMPT_VERSION
from app.rag.retriever import RetrievedChunk, retrieve


logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 5
MIN_SIMILARITY_SCORE = 0.25
CACHE_TTL_SECONDS = 10 * 60
MAX_CACHE_SIZE = 128
MAX_HISTORY_TURNS = 6

_quota_error_markers = ("429", "RESOURCE_EXHAUSTED")
_answer_cache: OrderedDict[tuple[Any, ...], tuple[float, "AnswerResult"]] = OrderedDict()


class ChatMessage(TypedDict):
    role: str
    content: str


class SourceCitation(TypedDict):
    filename: str | None
    page_number: int | None
    chunk_text: str
    score: float


class AnswerResult(TypedDict):
    answer: str
    sources: list[SourceCitation]
    retrieved_chunks: list[RetrievedChunk]
    used_chunks: list[RetrievedChunk]
    prompt_version: str
    cached: bool


def answer_question(
    query: str,
    chat_history: Sequence[ChatMessage | dict[str, str]] | None,
    document_ids: list[str] | None = None,
    session_id: str | None = None,
    db: Session | None = None,
) -> AnswerResult:
    cleaned_query = query.strip()
    normalized_query = _normalize_query(query)
    if not cleaned_query:
        return _empty_answer("I don't know.", cached=False)

    persisted_history = _load_recent_session_history(db, session_id)
    effective_history = [*persisted_history, *_normalize_chat_history(chat_history)]
    retrieval_query = rewrite_query_for_retrieval(cleaned_query, effective_history)
    normalized_document_ids = _normalize_document_ids(document_ids)
    cache_key = (
        session_id,
        normalized_query,
        _normalize_query(retrieval_query),
        normalized_document_ids,
        _history_cache_key(effective_history),
    )
    cached = _get_cached_answer(cache_key)
    if cached is not None:
        return {**cached, "cached": True}

    retrieved_chunks = retrieve(
        retrieval_query,
        top_k=DEFAULT_TOP_K,
        document_ids=list(normalized_document_ids) or None,
    )
    used_chunks = [
        chunk
        for chunk in retrieved_chunks
        if chunk["similarity_score"] >= MIN_SIMILARITY_SCORE
    ]

    if not used_chunks:
        result = {
            "answer": "I don't know. The provided context does not contain enough information to answer that.",
            "sources": [],
            "retrieved_chunks": retrieved_chunks,
            "used_chunks": [],
            "prompt_version": RAG_PROMPT_VERSION,
            "cached": False,
        }
        _set_cached_answer(cache_key, result)
        return result

    prompt = build_prompt(cleaned_query, used_chunks, effective_history)
    response = _invoke_llm_with_retry(prompt)
    result = {
        "answer": _response_text(response),
        "sources": deduplicate_sources(used_chunks),
        "retrieved_chunks": retrieved_chunks,
        "used_chunks": used_chunks,
        "prompt_version": RAG_PROMPT_VERSION,
        "cached": False,
    }
    _set_cached_answer(cache_key, result)
    return result


def rewrite_query_for_retrieval(
    query: str,
    chat_history: Sequence[ChatMessage | dict[str, str]],
) -> str:
    history = _format_chat_history(chat_history)
    if not history:
        return query

    prompt = (
        "Rewrite the current question as a standalone search query for retrieving "
        "enterprise document chunks. Use the conversation history only to resolve "
        "pronouns and references. Do not answer the question. Return only the "
        "rewritten search query.\n\n"
        f"Conversation history:\n{history}\n\n"
        f"Current question: {query}\n"
        "Standalone search query:"
    )
    rewritten_query = _response_text(_invoke_llm_with_retry(prompt))
    return rewritten_query or query


def deduplicate_sources(chunks: Sequence[RetrievedChunk]) -> list[SourceCitation]:
    sources_by_page: OrderedDict[tuple[str | None, str | None, int | None], SourceCitation] = OrderedDict()
    for chunk in chunks:
        key = (chunk["document_id"], chunk["source_filename"], chunk["page_number"])
        source = {
            "filename": chunk["source_filename"],
            "page_number": chunk["page_number"],
            "chunk_text": chunk["chunk_text"],
            "score": chunk["similarity_score"],
        }
        existing = sources_by_page.get(key)
        if existing is None:
            sources_by_page[key] = source
            continue
        if source["score"] > existing["score"]:
            sources_by_page[key] = source

    return list(sources_by_page.values())


def build_prompt(
    question: str,
    chunks: Sequence[RetrievedChunk],
    chat_history: Sequence[ChatMessage | dict[str, str]] | None = None,
) -> str:
    history = _format_chat_history(chat_history)
    prompt = RAG_PROMPT.format(
        context=_format_context(chunks),
        question=question,
    )
    if history:
        return (
            "Conversation history for resolving references only:\n"
            f"{history}\n\n"
            f"{prompt}"
        )

    return prompt


def _is_retryable_quota_error(error: BaseException) -> bool:
    error_text = f"{type(error).__name__}: {error}".upper()
    should_retry = any(marker in error_text for marker in _quota_error_markers)
    if should_retry:
        logger.warning("Retrying Gemini request after quota error: %s", error_text)
    return should_retry


@retry(
    retry=retry_if_exception(_is_retryable_quota_error),
    wait=wait_exponential(multiplier=1, min=1, max=20),
    stop=stop_after_attempt(4),
    reraise=True,
)
def _invoke_llm_with_retry(prompt: str) -> Any:
    return llm.invoke(prompt)


def _format_context(chunks: Sequence[RetrievedChunk]) -> str:
    context_blocks = []
    for index, chunk in enumerate(chunks, start=1):
        source = chunk["source_filename"] or "Unknown source"
        page = chunk["page_number"] if chunk["page_number"] is not None else "N/A"
        context_blocks.append(
            "[{index}] Source: {source}, page: {page}, similarity: {score:.3f}\n{text}".format(
                index=index,
                source=source,
                page=page,
                score=chunk["similarity_score"],
                text=chunk["chunk_text"],
            )
        )

    return "\n\n".join(context_blocks)


def _format_chat_history(
    chat_history: Sequence[ChatMessage | dict[str, str]] | None,
) -> str:
    if not chat_history:
        return ""

    formatted_messages = []
    for message in chat_history[-6:]:
        role = str(message.get("role", "user")).strip() or "user"
        content = str(message.get("content", "")).strip()
        if content:
            formatted_messages.append(f"{role}: {content}")

    return "\n".join(formatted_messages)


def _load_recent_session_history(db: Session | None, session_id: str | None) -> list[ChatMessage]:
    if db is None or not session_id:
        return []

    rows = list(
        db.scalars(
            select(ChatLog)
            .where(ChatLog.session_id == session_id)
            .order_by(ChatLog.created_at.desc(), ChatLog.id.desc())
            .limit(MAX_HISTORY_TURNS)
        )
    )
    rows.reverse()

    messages: list[ChatMessage] = []
    for row in rows:
        messages.append({"role": "user", "content": row.query})
        messages.append({"role": "assistant", "content": row.answer})

    return messages


def _normalize_chat_history(
    chat_history: Sequence[ChatMessage | dict[str, str]] | None,
) -> list[ChatMessage]:
    if not chat_history:
        return []

    messages: list[ChatMessage] = []
    for message in chat_history:
        content = str(message.get("content", "")).strip()
        if not content:
            continue
        role = str(message.get("role", "user")).strip() or "user"
        messages.append({"role": role, "content": content})

    return messages


def _history_cache_key(chat_history: Sequence[ChatMessage | dict[str, str]]) -> tuple[tuple[str, str], ...]:
    return tuple(
        (str(message.get("role", "")), _normalize_query(str(message.get("content", ""))))
        for message in chat_history[-(MAX_HISTORY_TURNS * 2):]
    )


def _normalize_query(query: str) -> str:
    return " ".join(query.strip().lower().split())


def _normalize_document_ids(document_ids: list[str] | None) -> tuple[str, ...]:
    if not document_ids:
        return ()
    return tuple(sorted({document_id.strip() for document_id in document_ids if document_id.strip()}))


def _get_cached_answer(
    cache_key: tuple[Any, ...],
) -> AnswerResult | None:
    cached = _answer_cache.get(cache_key)
    if cached is None:
        logger.info("CACHE MISS: %s", cache_key)
        return None

    created_at, result = cached
    if time.monotonic() - created_at > CACHE_TTL_SECONDS:
        logger.info("CACHE EXPIRED: %s", cache_key)
        _answer_cache.pop(cache_key, None)
        return None

    logger.info("CACHE HIT: %s", cache_key)
    _answer_cache.move_to_end(cache_key)
    return result


def _set_cached_answer(
    cache_key: tuple[Any, ...],
    result: AnswerResult,
) -> None:
    _answer_cache[cache_key] = (time.monotonic(), result)
    _answer_cache.move_to_end(cache_key)
    while len(_answer_cache) > MAX_CACHE_SIZE:
        _answer_cache.popitem(last=False)


def _response_text(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text", "")))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part).strip()
    return str(content).strip()


def _empty_answer(answer: str, cached: bool) -> AnswerResult:
    return {
        "answer": answer,
        "sources": [],
        "retrieved_chunks": [],
        "used_chunks": [],
        "prompt_version": RAG_PROMPT_VERSION,
        "cached": cached,
    }
