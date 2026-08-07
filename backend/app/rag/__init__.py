"""RAG module: shared embeddings instance + per-agent pgvector store manager."""
from ..config import VECTOR_DB_URL
from .embeddings import OpenRouterEmbeddings
from .store import RAGStoreManager

embeddings = OpenRouterEmbeddings()
store_manager = RAGStoreManager(embeddings, connection=VECTOR_DB_URL)

__all__ = ["store_manager"]
