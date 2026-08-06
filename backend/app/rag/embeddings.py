"""OpenRouter embeddings via the official /api/v1/embeddings endpoint.

langchain-openrouter only ships `ChatOpenRouter`, so we implement the
`langchain_core.embeddings.Embeddings` interface ourselves with httpx,
mirroring the documented OpenRouter API call.
"""
import httpx
from langchain_core.embeddings import Embeddings

from ..config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_EMBEDDING_MODEL,
    OPENROUTER_REFERER,
    OPENROUTER_TITLE,
    RAG_EMBED_BATCH_SIZE,
)


class OpenRouterEmbeddings(Embeddings):
    """Embeddings client for OpenRouter's `POST /embeddings` endpoint."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        batch_size: int = RAG_EMBED_BATCH_SIZE,
    ) -> None:
        self.api_key = api_key or OPENROUTER_API_KEY
        self.base_url = (base_url or OPENROUTER_BASE_URL).rstrip("/")
        self.model = model or OPENROUTER_EMBEDDING_MODEL
        self.batch_size = batch_size

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            # Optional but recommended by OpenRouter for rankings
            "HTTP-Referer": OPENROUTER_REFERER,
            "X-OpenRouter-Title": OPENROUTER_TITLE,
        }

    def _embed(self, texts: list[str]) -> list[list[float]]:
        """Call OpenRouter embeddings; returns vectors ordered like `texts`."""
        if not texts:
            return []
        response = httpx.post(
            f"{self.base_url}/embeddings",
            headers=self._headers(),
            json={
                "model": self.model,
                "input": texts,
                "encoding_format": "float",
            },
            timeout=60.0,
        )
        response.raise_for_status()
        payload = response.json()
        # Sort by index so order matches the input list
        data = sorted(payload.get("data", []), key=lambda item: item.get("index", 0))
        return [item["embedding"] for item in data]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed many texts, batching to stay within API limits."""
        vectors: list[list[float]] = []
        for i in range(0, len(texts), self.batch_size):
            vectors.extend(self._embed(texts[i : i + self.batch_size]))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query text."""
        return self._embed([text])[0]
