"""Resume file text extraction: PDF via pdfplumber, DOCX via python-docx."""
import os

from . import storage


def allowed_file(filename, allowed):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


def extract_text(stored_key, ext):
    """Extract text from a stored upload (storage backend or local fallback)."""
    with storage.open_file(stored_key) as source:
        if ext == "pdf":
            return _extract_pdf(source)
        if ext == "docx":
            return _extract_docx(source)
    raise ValueError(f"Unsupported extension: {ext}")


def _extract_pdf(source):
    import pdfplumber
    chunks = []
    with pdfplumber.open(source) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if text.strip():
                chunks.append(text)
    return "\n".join(chunks).strip()


def _extract_docx(source):
    import docx
    document = docx.Document(source)
    parts = []
    for para in document.paragraphs:
        if para.text.strip():
            parts.append(para.text.strip())
    for table in document.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    return "\n".join(parts).strip()


def save_upload(data, filename, user_id):
    """Store uploaded bytes via the storage backend with a collision-safe name.

    Returns (stored_name, ext). Extension comes from the original filename,
    which the route has already validated with allowed_file().
    """
    import uuid
    ext = filename.rsplit(".", 1)[1].lower()
    stored = f"u{user_id}_{uuid.uuid4().hex[:12]}.{ext}"
    storage.save_bytes(stored, data, content_type="application/octet-stream")
    return stored, ext
