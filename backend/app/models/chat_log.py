import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ChatLog(Base):
    __tablename__ = "chat_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    sources_json: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    @property
    def sources(self) -> list[dict[str, Any]]:
        return json.loads(self.sources_json)

    @sources.setter
    def sources(self, value: list[dict[str, Any]]) -> None:
        self.sources_json = json.dumps(value, ensure_ascii=False)
