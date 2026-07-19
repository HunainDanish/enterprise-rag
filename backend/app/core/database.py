from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    import app.models.chat_log  # noqa: F401
    import app.models.document  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_chat_log_schema()


def _ensure_sqlite_chat_log_schema() -> None:
    if not settings.DATABASE_URL.startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "chat_logs" not in inspector.get_table_names():
        return

    column_names = {column["name"] for column in inspector.get_columns("chat_logs")}
    if "session_id" in column_names:
        return

    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE chat_logs ADD COLUMN session_id VARCHAR DEFAULT 'default' NOT NULL")
        )
