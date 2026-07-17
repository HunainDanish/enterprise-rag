from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, documents, search
from app.core.config import settings

app = FastAPI(title="Enterprise Document Intelligence Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(search.router, prefix="/api/search", tags=["search"])


@app.get("/health")
def health() -> dict[str, str]:
    """Return a lightweight readiness response for the frontend and deployments."""
    return {"status": "ok"}
