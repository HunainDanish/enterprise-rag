from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.chat_log import ChatLog
from app.models.document import Document

router = APIRouter()


class DashboardStats(BaseModel):
    total_documents: int
    total_chunks: int
    total_questions: int


@router.get("", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)) -> DashboardStats:
    total_documents = db.scalar(select(func.count(Document.id))) or 0
    total_chunks = db.scalar(select(func.coalesce(func.sum(Document.num_chunks), 0))) or 0
    total_questions = db.scalar(select(func.count(ChatLog.id))) or 0

    return DashboardStats(
        total_documents=total_documents,
        total_chunks=total_chunks,
        total_questions=total_questions,
    )
