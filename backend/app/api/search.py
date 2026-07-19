from fastapi import APIRouter, Query

from app.rag.retriever import RetrievedChunk, retrieve

router = APIRouter()


@router.get("")
def search(
    q: str = Query(min_length=1),
    top_k: int = Query(default=5, ge=1, le=25),
    document_ids: list[str] | None = Query(default=None),
) -> dict[str, str | int | list[str] | list[RetrievedChunk] | None]:
    results = retrieve(q, top_k=top_k, document_ids=document_ids)
    return {
        "query": q,
        "top_k": top_k,
        "document_ids": document_ids,
        "results": results,
    }
