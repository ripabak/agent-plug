"""RAG module: shared embeddings instance + per-agent in-memory store manager."""
from .embeddings import OpenRouterEmbeddings
from .store import RAGStoreManager

embeddings = OpenRouterEmbeddings()
store_manager = RAGStoreManager(embeddings)

__all__ = ["store_manager"]
