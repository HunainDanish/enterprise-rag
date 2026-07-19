from typing import Any, TypedDict

from langchain_core.documents import Document as LangChainDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings
from app.rag.loaders import PageText


class ChunkText(TypedDict):
    page_content: str
    metadata: dict[str, Any]


def chunk_pages(
    document_id: str,
    filename: str,
    pages: list[PageText],
) -> list[LangChainDocument]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=[
        "\n\n",
        "\n",
        ". ",
        "? ",
        "! ",
        "; ",
        ", ",
        " ",
        "",
    ],
    )
    page_documents = [
        LangChainDocument(
            page_content=page["text"],
            metadata={
                "document_id": document_id,
                "filename": filename,
                "page_number": page["page_number"],
            },
        )
        for page in pages
        if page["text"].strip()
    ]

    chunks = splitter.split_documents(page_documents)
    for index, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = index

    return chunks


def serialize_chunks(chunks: list[LangChainDocument]) -> list[ChunkText]:
    return [
        {
            "page_content": chunk.page_content,
            "metadata": dict(chunk.metadata),
        }
        for chunk in chunks
    ]
