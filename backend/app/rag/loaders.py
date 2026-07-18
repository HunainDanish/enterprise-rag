import re
import zipfile
from pathlib import Path
from typing import TypedDict
from xml.etree import ElementTree

from pypdf import PdfReader


class PageText(TypedDict):
    page_number: int | None
    text: str


def load_pdf(path: Path) -> list[PageText]:
    reader = PdfReader(path)
    return [
        {
            "page_number": index,
            "text": page.extract_text() or "",
        }
        for index, page in enumerate(reader.pages, start=1)
    ]


def load_txt(path: Path) -> list[PageText]:
    return [{"page_number": None, "text": path.read_text(encoding="utf-8", errors="ignore")}]


def load_markdown(path: Path) -> list[PageText]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    text = re.sub(r"```[\s\S]*?```", lambda match: match.group(0).strip("`"), text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[*_~`]+", "", text)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    return [{"page_number": None, "text": text}]


def load_docx(path: Path) -> list[PageText]:
    try:
        from docx import Document as DocxDocument
    except ImportError:
        return _load_docx_from_xml(path)

    document = DocxDocument(path)
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    return [{"page_number": None, "text": text}]


def _load_docx_from_xml(path: Path) -> list[PageText]:
    with zipfile.ZipFile(path) as docx:
        xml = docx.read("word/document.xml")

    root = ElementTree.fromstring(xml)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", namespace):
        runs = [
            node.text or ""
            for node in paragraph.findall(".//w:t", namespace)
        ]
        if runs:
            paragraphs.append("".join(runs))

    return [{"page_number": None, "text": "\n".join(paragraphs)}]


def load_document(path: Path, filetype: str) -> list[PageText]:
    loaders = {
        "pdf": load_pdf,
        "txt": load_txt,
        "md": load_markdown,
        "docx": load_docx,
    }

    try:
        loader = loaders[filetype.lower()]
    except KeyError as exc:
        raise ValueError(f"Unsupported file type: {filetype}") from exc

    return loader(path)
