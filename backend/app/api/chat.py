from pydantic import BaseModel, Field
from fastapi import APIRouter

from app.rag.chain import AnswerResult, ChatMessage, answer_question

router = APIRouter()


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    chat_history: list[ChatMessage] = Field(default_factory=list)
    document_ids: list[str] | None = None


@router.post("")
def chat(request: ChatRequest) -> AnswerResult:
    return answer_question(
        request.question,
        request.chat_history,
        document_ids=request.document_ids,
    )
