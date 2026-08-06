"""Text chunking for RAG (official LangChain recommendation)."""
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..config import RAG_CHUNK_OVERLAP, RAG_CHUNK_SIZE


def make_splitter(chunk_size: int = RAG_CHUNK_SIZE, chunk_overlap: int = RAG_CHUNK_OVERLAP):
    """Create a RecursiveCharacterTextSplitter (defaults from env)."""
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def split_text(text: str, chunk_size: int = RAG_CHUNK_SIZE, chunk_overlap: int = RAG_CHUNK_OVERLAP) -> list[str]:
    """Split plain text into chunks."""
    return make_splitter(chunk_size, chunk_overlap).split_text(text)
