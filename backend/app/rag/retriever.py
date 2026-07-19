from typing import Any, TypedDict

from app.rag.embeddings import encode_texts
from app.rag.vectorstore import query as query_vectorstore


class RetrievedChunk(TypedDict):
    document_id: str | None
    source_filename: str | None
    page_number: int | None
    chunk_index: int | None
    chunk_text: str
    similarity_score: float
    distance: float | None


def retrieve(
    query: str,
    top_k: int = 5,
    document_ids: list[str] | None = None,
) -> list[RetrievedChunk]:
    cleaned_query = query.strip()
    if not cleaned_query:
        return []

    query_embedding = encode_texts([cleaned_query])[0]
    results = query_vectorstore(
        query_embedding,
        top_k,
        filter=_document_filter(document_ids),
    )
    return _format_results(results)


def _document_filter(document_ids: list[str] | None) -> dict[str, Any] | None:
    if not document_ids:
        return None

    cleaned_ids = [document_id.strip() for document_id in document_ids if document_id.strip()]
    if not cleaned_ids:
        return None

    if len(cleaned_ids) == 1:
        return {"document_id": cleaned_ids[0]}

    return {"document_id": {"$in": cleaned_ids}}


def _format_results(results: dict[str, Any]) -> list[RetrievedChunk]:
    documents = _first_result_list(results.get("documents"))
    metadatas = _first_result_list(results.get("metadatas"))
    distances = _first_result_list(results.get("distances"))

    formatted: list[RetrievedChunk] = []
    for index, chunk_text in enumerate(documents):
        metadata = metadatas[index] if index < len(metadatas) and metadatas[index] else {}
        distance = distances[index] if index < len(distances) else None
        formatted.append(
            {
                "document_id": _as_optional_str(metadata.get("document_id")),
                "source_filename": _as_optional_str(metadata.get("filename")),
                "page_number": _page_number(metadata.get("page_number")),
                "chunk_index": _as_optional_int(metadata.get("chunk_index")),
                "chunk_text": chunk_text or "",
                "similarity_score": _similarity_score(distance),
                "distance": distance,
            }
        )

    return formatted


def _first_result_list(value: Any) -> list[Any]:
    if not value:
        return []
    if isinstance(value, list) and value and isinstance(value[0], list):
        return value[0]
    if isinstance(value, list):
        return value
    return []


def _page_number(value: Any) -> int | None:
    page_number = _as_optional_int(value)
    if page_number == 0:
        return None
    return page_number


def _as_optional_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _similarity_score(distance: Any) -> float:
    if distance is None:
        return 0.0
    return 1.0 / (1.0 + float(distance))
