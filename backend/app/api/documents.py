import shutil
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.document import Document, DocumentRead
from app.rag.processing import process_document
from app.rag.vectorstore import delete_document as delete_document_vectors


router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}


def _safe_filename(filename: str | None) -> str:
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must include a filename.",
        )

    safe_name = PurePosixPath(PureWindowsPath(filename).name).name
    if safe_name in {"", ".", ".."}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must include a valid filename.",
        )

    return safe_name


def _file_extension(filename: str) -> str:
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed extensions: {allowed}.",
        )

    return extension.lstrip(".")


def _get_document_or_404(document_id: str, db: Session) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    return document


def _document_dir(document_id: str) -> Path:
    return settings.UPLOAD_DIR / document_id


def _document_source_path(document: Document) -> Path:
    return _document_dir(document.id) / document.filename


@router.post("/upload", response_model=list[DocumentRead], status_code=status.HTTP_201_CREATED)
def upload_documents(
    files: Annotated[list[UploadFile], File(description="One or more documents to upload")],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> list[DocumentRead]:
    documents: list[Document] = []
    saved_files: list[tuple[Document, Path]] = []

    for upload in files:
        filename = _safe_filename(upload.filename)
        filetype = _file_extension(filename)
        document_id = str(uuid4())
        document_dir = settings.UPLOAD_DIR / document_id
        destination = document_dir / filename

        document_dir.mkdir(parents=True, exist_ok=False)
        try:
            with destination.open("wb") as target:
                shutil.copyfileobj(upload.file, target)
        except OSError as exc:
            shutil.rmtree(document_dir, ignore_errors=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save uploaded file.",
            ) from exc

        document = Document(
            id=document_id,
            filename=filename,
            filetype=filetype,
            status="pending",
        )
        db.add(document)
        documents.append(document)
        saved_files.append((document, destination))

    db.commit()
    for document in documents:
        db.refresh(document)
        document.status = "processing"

    db.commit()
    for document, destination in saved_files:
        db.refresh(document)
        background_tasks.add_task(
            process_document,
            document.id,
            str(destination),
            document.filetype,
        )

    return [DocumentRead.model_validate(document) for document in documents]


@router.get("", response_model=list[DocumentRead])
def list_documents(db: Session = Depends(get_db)) -> list[Document]:
    return list(db.scalars(select(Document).order_by(Document.upload_time.desc())))


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str, db: Session = Depends(get_db)) -> None:
    document = _get_document_or_404(document_id, db)

    try:
        delete_document_vectors(document.id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document vectors.",
        ) from exc

    upload_dir = _document_dir(document.id)
    if upload_dir.exists():
        try:
            shutil.rmtree(upload_dir)
        except OSError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete uploaded document files.",
            ) from exc

    db.delete(document)
    db.commit()


@router.post("/{document_id}/refresh", response_model=DocumentRead, status_code=status.HTTP_202_ACCEPTED)
def refresh_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> DocumentRead:
    document = _get_document_or_404(document_id, db)
    if document.status in {"processing", "embedding"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is already being processed.",
        )

    source_path = _document_source_path(document)
    if not source_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Original uploaded file was not found.",
        )

    document.status = "processing"
    db.commit()
    db.refresh(document)
    background_tasks.add_task(
        process_document,
        document.id,
        str(source_path),
        document.filetype,
    )

    return DocumentRead.model_validate(document)
