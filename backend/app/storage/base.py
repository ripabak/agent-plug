"""Storage backend interface for uploaded knowledge files (PDFs).

Backends: `LocalStorage` (filesystem, default) and `S3Storage`
(S3-compatible object storage — SeaweedFS / MinIO / AWS S3).

Keys are portable identifiers: a relative path under `UPLOAD_DIR` locally,
an object key in the bucket on S3. That keeps `Source.file_path` and the
`file://…` citation URLs identical on both backends.
"""

from typing import Protocol


class Storage(Protocol):
    """Async object-storage operations. All methods are concurrency-safe."""

    async def put(self, key: str, data: bytes, content_type: str | None = None) -> None:
        """Write (or overwrite) an object under `key`."""
        ...

    async def get(self, key: str) -> bytes:
        """Read the object; raises if missing."""
        ...

    async def delete(self, key: str) -> None:
        """Delete the object. Idempotent — missing objects are not an error."""
        ...

    async def exists(self, key: str) -> bool:
        """True if the object exists."""
        ...

    async def replace(self, key: str, data: bytes, content_type: str | None = None) -> None:
        """Overwrite an existing object in place (keeps the same key/URL)."""
        ...
