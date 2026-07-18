from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application configuration loaded from ``backend/.env``."""

    GOOGLE_API_KEY: str
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173"]
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    DATABASE_URL: str = f"sqlite:///{BACKEND_DIR / 'app' / 'documents.db'}"
    UPLOAD_DIR: Path = BACKEND_DIR / "app" / "uploads"

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
