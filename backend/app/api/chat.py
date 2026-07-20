import json
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.chat_log import ChatLog, ChatSession
from app.rag.chain import ChatMessage, SourceCitation, answer_question

router = APIRouter()


class ChatRequest(BaseModel):
    question: str | None = Field(default=None, min_length=1)
    query: str | None = Field(default=None, min_length=1)
    session_id: str | None = None
    chat_history: list[ChatMessage] = Field(default_factory=list)
    document_ids: list[str] | None = None

    @model_validator(mode="after")
    def require_question_or_query(self) -> "ChatRequest":
        if self.question is None and self.query is None:
            raise ValueError("Either question or query is required.")
        return self

    @property
    def prompt_text(self) -> str:
        return (self.query or self.question or "").strip()


class ChatSource(BaseModel):
    filename: str | None
    page_number: int | None
    chunk_text: str
    score: float


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources: list[ChatSource]


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    session_id = _normalize_session_id(request.session_id)
    _ensure_session(db, session_id)
    result = answer_question(
        request.prompt_text,
        request.chat_history,
        document_ids=request.document_ids,
        session_id=session_id,
        db=db,
    )
    response = ChatResponse(
        session_id=session_id,
        answer=result["answer"],
        sources=result["sources"],
    )
    _log_chat_interaction(db, session_id, request.prompt_text, result["sources"], result["answer"])
    return response


class ChatHistoryTurn(BaseModel):
    id: int
    query: str
    answer: str
    sources: list[ChatSource]
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    session_id: str
    history: list[ChatHistoryTurn]


@router.get("/{session_id}/history", response_model=ChatHistoryResponse)
def get_chat_history(session_id: str, db: Session = Depends(get_db)) -> ChatHistoryResponse:
    turns = list(
        db.scalars(
            select(ChatLog)
            .where(ChatLog.session_id == session_id)
            .order_by(ChatLog.created_at.asc(), ChatLog.id.asc())
        )
    )
    return ChatHistoryResponse(
        session_id=session_id,
        history=[
            ChatHistoryTurn(
                id=turn.id,
                query=turn.query,
                answer=turn.answer,
                sources=turn.sources,
                created_at=turn.created_at,
            )
            for turn in turns
        ],
    )


@router.delete("/{session_id}")
def clear_chat_session(session_id: str, db: Session = Depends(get_db)) -> dict[str, str | int]:
    deleted_turns = db.execute(delete(ChatLog).where(ChatLog.session_id == session_id)).rowcount or 0
    db.execute(delete(ChatSession).where(ChatSession.id == session_id))
    db.commit()
    return {"session_id": session_id, "deleted_turns": deleted_turns}


def _log_chat_interaction(
    db: Session,
    session_id: str,
    query: str,
    sources: list[SourceCitation],
    answer: str,
) -> None:
    chat_log = ChatLog(
        session_id=session_id,
        query=query,
        sources_json=json.dumps(sources, ensure_ascii=False),
        answer=answer,
    )
    db.add(chat_log)
    session = db.get(ChatSession, session_id)
    if session is not None:
        session.updated_at = datetime.now(timezone.utc)
    db.commit()


def _normalize_session_id(session_id: str | None) -> str:
    if session_id and session_id.strip():
        return session_id.strip()
    return str(uuid4())


def _ensure_session(db: Session, session_id: str) -> None:
    session = db.get(ChatSession, session_id)
    if session is not None:
        return

    db.add(ChatSession(id=session_id))
    db.commit()
