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
