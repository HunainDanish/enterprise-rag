from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict
from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    filetype: Mapped[str] = mapped_column(String, nullable=False, index=True)
    upload_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    num_pages: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    num_chunks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False, index=True)

    @property
    def chunk_count(self) -> int:
        return self.num_chunks


class DocumentRead(BaseModel):
    id: str
    filename: str
    filetype: str
    upload_time: datetime
    num_pages: int
    num_chunks: int
    chunk_count: int
    status: str

    model_config = ConfigDict(from_attributes=True)
