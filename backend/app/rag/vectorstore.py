import logging
from typing import Any, Sequence

import chromadb
from langchain_core.documents import Document as LangChainDocument

from app.core.config import settings
from app.rag.embeddings import EMBEDDING_DIMENSION


logger = logging.getLogger(__name__)

VECTORDB_PATH = "app/vectordb"
COLLECTION_NAME = "documents"
PROBE_ID = "__dimension_probe__"

_client = chromadb.PersistentClient(path=VECTORDB_PATH)


def _collection_metadata() -> dict[str, str | int]:
    return {
        "embedding_model": settings.EMBEDDING_MODEL,
        "embedding_dimension": EMBEDDING_DIMENSION,
    }


def _load_collection():
    collection = _client.get_or_create_collection(
        COLLECTION_NAME,
        metadata=_collection_metadata(),
    )
    stored_dimension = _stored_embedding_dimension(collection)
    if stored_dimension is None:
        return _ensure_empty_collection_accepts_expected_dimension(collection)

    if stored_dimension != EMBEDDING_DIMENSION:
        logger.warning(
            "Recreating Chroma collection %s because it expects embeddings with "
            "dimension %s, but %s produces dimension %s.",
            COLLECTION_NAME,
            stored_dimension,
            settings.EMBEDDING_MODEL,
            EMBEDDING_DIMENSION,
        )
        return _recreate_collection()

    _sync_collection_metadata(collection)
    return collection


def _recreate_collection():
    _client.delete_collection(COLLECTION_NAME)
    return _client.get_or_create_collection(
        COLLECTION_NAME,
        metadata=_collection_metadata(),
    )


def _sync_collection_metadata(collection) -> None:
    if collection.metadata != _collection_metadata():
        collection.modify(metadata=_collection_metadata())


def _stored_embedding_dimension(collection) -> int | None:
    if collection.count() == 0:
        return None

    result = collection.get(limit=1, include=["embeddings"])
    embeddings = result.get("embeddings")
    if embeddings is None or len(embeddings) == 0:
        return None

    return len(embeddings[0])


def _ensure_empty_collection_accepts_expected_dimension(collection):
    try:
        collection.add(
            ids=[PROBE_ID],
            documents=["dimension probe"],
            embeddings=[_zero_embedding()],
            metadatas=[{"document_id": PROBE_ID, "chunk_index": -1}],
        )
        collection.delete(ids=[PROBE_ID])
        _sync_collection_metadata(collection)
        return collection
    except Exception:
        logger.warning(
            "Recreating empty Chroma collection %s because it does not accept "
            "%s-dimensional embeddings from %s.",
            COLLECTION_NAME,
            EMBEDDING_DIMENSION,
            settings.EMBEDDING_MODEL,
            exc_info=True,
        )
        recreated = _recreate_collection()
        recreated.add(
            ids=[PROBE_ID],
            documents=["dimension probe"],
            embeddings=[_zero_embedding()],
            metadatas=[{"document_id": PROBE_ID, "chunk_index": -1}],
        )
        recreated.delete(ids=[PROBE_ID])
        return recreated


def _zero_embedding() -> list[float]:
    return [0.0] * EMBEDDING_DIMENSION


_collection = _load_collection()


def add_chunks(
    document_id: str,
    chunks: list[LangChainDocument],
    embeddings: list[list[float]],
) -> None:
    if len(chunks) != len(embeddings):
        raise ValueError("Chunk and embedding counts must match.")

    _validate_embedding_dimensions(embeddings)
    delete_document(document_id)
    if not chunks:
        return

    ids = [_chunk_id(document_id, chunk) for chunk in chunks]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate chunk IDs generated for ChromaDB insert.")

    documents = [chunk.page_content for chunk in chunks]
    metadatas = [_metadata_with_document_id(document_id, chunk) for chunk in chunks]

    try:
        _collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
    except Exception:
        logger.exception(
            "Failed to insert %s chunks for document %s into ChromaDB.",
            len(chunks),
            document_id,
        )
        raise


def delete_document(document_id: str) -> None:
    _collection.delete(where={"document_id": document_id})


def query(
    embedding: list[float],
    top_k: int,
    filter: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    _validate_embedding_dimensions([embedding])
    return _collection.query(
        query_embeddings=[embedding],
        n_results=top_k,
        where=filter,
        include=["documents", "metadatas", "distances"],
    )


def _validate_embedding_dimensions(embeddings: Sequence[Sequence[float]]) -> None:
    for index, embedding in enumerate(embeddings):
        if len(embedding) != EMBEDDING_DIMENSION:
            raise ValueError(
                f"Embedding at index {index} has dimension {len(embedding)}; "
                f"expected {EMBEDDING_DIMENSION} for {settings.EMBEDDING_MODEL}."
            )


def _chunk_id(document_id: str, chunk: LangChainDocument) -> str:
    return f"{document_id}:{chunk.metadata['chunk_index']}"


def _metadata_with_document_id(
    document_id: str,
    chunk: LangChainDocument,
) -> dict[str, str | int | float | bool]:
    metadata = {
        **chunk.metadata,
        "document_id": document_id,
    }
    if metadata.get("page_number") is None:
        metadata["page_number"] = 0

    return {
        key: value
        for key, value in metadata.items()
        if isinstance(value, str | int | float | bool)
    }
def get_collection():
    return _collection