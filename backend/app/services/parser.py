"""Extract plain text from uploaded resume files."""
import io
import re
from pathlib import Path

from docx import Document
from pypdf import PdfReader

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
MIN_TEXT_LENGTH = 50


class ParseError(ValueError):
    """Raised when a file cannot be converted into usable text."""


def _from_pdf(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ParseError("The PDF is password protected. Please upload an unlocked copy.")
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except ParseError:
        raise
    except Exception as exc:
        raise ParseError("The PDF could not be read. It may be corrupted.") from exc


def _from_docx(data: bytes) -> str:
    try:
        doc = Document(io.BytesIO(data))
    except Exception as exc:
        raise ParseError("The DOCX file could not be read. It may be corrupted.") from exc
    parts = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            parts.append(" | ".join(cell.text.strip() for cell in row.cells))
    return "\n".join(parts)


def extract_text(filename: str, data: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        text = _from_pdf(data)
    elif ext == ".docx":
        text = _from_docx(data)
    elif ext == ".txt":
        text = data.decode("utf-8", errors="ignore")
    else:
        raise ParseError("Unsupported file type. Please upload a PDF, DOCX or TXT file.")

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) < MIN_TEXT_LENGTH:
        raise ParseError(
            "No readable text was found. If this is a scanned document, please upload a text-based version."
        )
    return text
