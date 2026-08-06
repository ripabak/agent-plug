"""PDF text extraction for RAG ingestion (pypdf)."""
from pathlib import Path

from pypdf import PdfReader


def parse_pdf(path: str | Path) -> str:
    """Extract text from a PDF file, joining pages with blank lines.

    Raises on unreadable/corrupt files so the source is marked `failed`.
    """
    reader = PdfReader(str(path))
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text.strip())
    if not pages:
        raise ValueError("PDF contains no extractable text")
    return "\n\n".join(pages)
