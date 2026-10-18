"""Resume file -> plain text. PDF, DOCX and TXT only; no OCR."""

from io import BytesIO
from pathlib import PurePath

MAX_BYTES = 5 * 1024 * 1024


class ResumeError(ValueError):
    pass


def extract_text(filename: str, data: bytes) -> str:
    if len(data) > MAX_BYTES:
        raise ResumeError("Resume is larger than 5 MB.")
    ext = PurePath(filename).suffix.lower()
    if ext == ".pdf":
        from pypdf import PdfReader

        text = "\n".join(p.extract_text() or "" for p in PdfReader(BytesIO(data)).pages)
    elif ext == ".docx":
        from docx import Document

        doc = Document(BytesIO(data))
        parts = [p.text for p in doc.paragraphs]
        parts += [c.text for t in doc.tables for row in t.rows for c in row.cells]
        text = "\n".join(parts)
    elif ext == ".txt":
        text = data.decode("utf-8", errors="replace")
    else:
        raise ResumeError(f"Unsupported file type {ext!r}; upload PDF, DOCX or TXT.")
    text = "\n".join(ln.rstrip() for ln in text.splitlines() if ln.strip())
    if len(text) < 50:
        raise ResumeError("Could not read text from the resume (scanned PDFs are not supported).")
    return text
