"""Extract plain text from an uploaded resume. No network, no OCR."""

import io
import re
from pathlib import Path

SUPPORTED_SUFFIXES = frozenset({".pdf", ".docx", ".txt"})


class UnsupportedFormat(ValueError):
    pass


class EmptyResume(ValueError):
    pass


def extract_text(filename: str, data: bytes, *, max_chars: int = 50_000) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise UnsupportedFormat(f"Unsupported resume format: {suffix or 'unknown'}")

    if suffix == ".pdf":
        text = _from_pdf(data)
    elif suffix == ".docx":
        text = _from_docx(data)
    else:
        text = _from_txt(data)

    text = _normalize(text)
    if not text:
        raise EmptyResume("No extractable text in resume")
    return text[:max_chars]


def _from_txt(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1", errors="replace")


def _from_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:  # noqa: BLE001 - any parse failure means no usable text
        raise EmptyResume("Could not read PDF") from exc


def _from_docx(data: bytes) -> str:
    from docx import Document

    try:
        document = Document(io.BytesIO(data))
    except Exception as exc:  # noqa: BLE001 - any parse failure means no usable text
        raise EmptyResume("Could not read DOCX") from exc

    parts = [paragraph.text for paragraph in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                parts.append(cell.text)
    return "\n".join(parts)


def _normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
