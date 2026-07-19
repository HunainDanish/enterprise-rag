import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.document import Document
from app.rag.chunking import ChunkText, chunk_pages, serialize_chunks
from app.rag.cleaning import clean_pages
from app.rag.embeddings import encode_texts
from app.rag.loaders import PageText, load_document
from app.rag.vectorstore import add_chunks


EXTRACTED_TEXT_FILENAME = "extracted_pages.json"
CHUNKS_FILENAME = "chunks.json"
EMBEDDINGS_FILENAME = "embeddings.json"

logger = logging.getLogger(__name__)


def extracted_text_path(document_id: str) -> Path:
    return settings.UPLOAD_DIR / document_id / EXTRACTED_TEXT_FILENAME


def chunks_path(document_id: str) -> Path:
    return settings.UPLOAD_DIR / document_id / CHUNKS_FILENAME


def embeddings_path(document_id: str) -> Path:
    return settings.UPLOAD_DIR / document_id / EMBEDDINGS_FILENAME


def process_document(document_id: str, file_path: str, filetype: str) -> None:
    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if document is None:
            return

        document.status = "processing"
        db.commit()

        pages = load_document(Path(file_path), filetype)
        cleaned_pages = clean_pages(pages)
        print("\n===== EXTRACTION PREVIEW =====")
        print(cleaned_pages[0]["text"][:200] if cleaned_pages else "")
        print("==============================")
        _write_extracted_pages(extracted_text_path(document_id), cleaned_pages)
        chunks = chunk_pages(document.id, document.filename, cleaned_pages)
        print(f"Generated {len(chunks)} chunks")
        for chunk in chunks[:3]:
            print("\n===================")
            print(chunk.metadata)
            print("Chunk:", chunk.metadata["chunk_index"])
            print("Page:", chunk.metadata["page_number"])
            print("Document:", chunk.metadata["filename"])
            print(chunk.page_content[:300])
        _write_chunks(chunks_path(document_id), serialize_chunks(chunks))
        document.status = "embedding"
        db.commit()

        embeddings = encode_texts([chunk.page_content for chunk in chunks])
        _write_embeddings(embeddings_path(document_id), embeddings)
        add_chunks(document.id, chunks, embeddings)

        document.num_pages = len(cleaned_pages)
        document.num_chunks = len(chunks)
        document.status = "ready"
        db.commit()
    except Exception:
        logger.exception("Failed to process document %s.", document_id)
        db.rollback()
        _mark_failed(db, document_id)
    finally:
        db.close()


def _write_extracted_pages(path: Path, pages: list[PageText]) -> None:
    path.write_text(
        json.dumps(pages, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_chunks(path: Path, chunks: list[ChunkText]) -> None:
    path.write_text(
        json.dumps(chunks, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_embeddings(path: Path, embeddings: list[list[float]]) -> None:
    path.write_text(
        json.dumps(embeddings),
        encoding="utf-8",
    )


def _mark_failed(db: Session, document_id: str) -> None:
    document = db.get(Document, document_id)
    if document is None:
        return

    document.status = "failed"
    db.commit()
