from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.api import chat, documents, search
from app.core.config import settings
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(
    title="Enterprise Document Intelligence Platform",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(search.router, prefix="/api/search", tags=["search"])


def _fix_uploadfile_schema(schema: dict) -> None:
    if not isinstance(schema, dict):
        return

    if schema.get("contentMediaType") == "application/octet-stream":
        schema.pop("contentMediaType", None)
        schema["format"] = "binary"

    for value in schema.values():
        if isinstance(value, dict):
            _fix_uploadfile_schema(value)
        elif isinstance(value, list):
            for item in value:
                _fix_uploadfile_schema(item)


def custom_openapi() -> dict:
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )
    _fix_uploadfile_schema(openapi_schema)
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/health")
def health() -> dict[str, str]:
    """Return a lightweight readiness response for the frontend and deployments."""
    return {"status": "ok"}
