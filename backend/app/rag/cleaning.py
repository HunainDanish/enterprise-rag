import re
import string

from app.rag.loaders import PageText


PRINTABLE = set(string.printable)


def remove_non_printable(text: str) -> str:
    return "".join(char if char in PRINTABLE or char.isprintable() else " " for char in text)


def collapse_whitespace(text: str) -> str:
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _edge_lines(text: str) -> tuple[str | None, str | None]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None, None
    return lines[0], lines[-1]


def _repeated_edge_lines(pages: list[PageText]) -> set[str]:
    if len(pages) < 3:
        return set()

    counts: dict[str, int] = {}
    for page in pages:
        for line in _edge_lines(page["text"]):
            if line and len(line) <= 120:
                counts[line] = counts.get(line, 0) + 1

    threshold = max(3, int(len(pages) * 0.6))
    return {line for line, count in counts.items() if count >= threshold}


def clean_text(text: str) -> str:
    text = remove_non_printable(text)
    text = re.sub(r"[\u200b-\u200f\ufeff]", "", text)
    return collapse_whitespace(text)


def clean_pages(pages: list[PageText]) -> list[PageText]:
    cleaned_pages = [
        {"page_number": page["page_number"], "text": clean_text(page["text"])}
        for page in pages
    ]
    repeated_lines = _repeated_edge_lines(cleaned_pages)
    if not repeated_lines:
        return cleaned_pages

    result: list[PageText] = []
    for page in cleaned_pages:
        lines = [
            line
            for line in page["text"].splitlines()
            if line.strip() not in repeated_lines
        ]
        result.append(
            {
                "page_number": page["page_number"],
                "text": "\n".join(lines).strip(),
            }
        )

    return result
