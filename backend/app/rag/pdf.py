"""PDF text extraction for RAG ingestion (pypdf)."""
import io
from pathlib import Path

from pypdf import PdfReader


def parse_pdf(path: str | Path) -> str:
    """Extract text from a PDF file on disk, joining pages with blank lines.

    Raises on unreadable/corrupt files so the source is marked `failed`.
    """
    return parse_pdf_bytes(Path(path).read_bytes())


def parse_pdf_bytes(data: bytes) -> str:
    """Extract text from PDF bytes (e.g. read from S3), joining pages.

    Raises on unreadable/corrupt files so the source is marked `failed`.
    """
    reader = PdfReader(io.BytesIO(data))
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text.strip())
    if not pages:
        raise ValueError("PDF contains no extractable text")
    return "\n\n".join(pages)
