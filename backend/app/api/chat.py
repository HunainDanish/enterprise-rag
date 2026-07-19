import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.chat_log import ChatLog
from app.rag.chain import ChatMessage, SourceCitation, answer_question

router = APIRouter()


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    chat_history: list[ChatMessage] = Field(default_factory=list)
    document_ids: list[str] | None = None


class ChatSource(BaseModel):
    filename: str | None
    page_number: int | None
    chunk_text: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource]


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    result = answer_question(
        request.question,
        request.chat_history,
        document_ids=request.document_ids,
    )
    response = ChatResponse(
        answer=result["answer"],
        sources=result["sources"],
    )
    _log_chat_interaction(db, request.question, result["sources"], result["answer"])
    return response


def _log_chat_interaction(
    db: Session,
    query: str,
    sources: list[SourceCitation],
    answer: str,
) -> None:
    chat_log = ChatLog(
        query=query,
        sources_json=json.dumps(sources, ensure_ascii=False),
        answer=answer,
    )
    db.add(chat_log)
    db.commit()
