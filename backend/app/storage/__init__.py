"""Storage backend factory: one shared instance selected by STORAGE_BACKEND.

- `local` (default): filesystem under UPLOAD_DIR (existing behavior)
- `s3`: S3-compatible object storage (SeaweedFS / MinIO / AWS)

`app.storage.storage` is the process-wide singleton used by routers and the
RAG pipeline, mirroring `app.rag.store_manager`.
"""

from ..config import (
    S3_ACCESS_KEY,
    S3_BUCKET,
    S3_ENDPOINT_URL,
    S3_PREFIX,
    S3_REGION,
    S3_SECRET_KEY,
    STORAGE_BACKEND,
)
from .local import LocalStorage
from .s3 import S3Storage


def build_storage() -> LocalStorage | S3Storage:
    """Create a storage backend from the current configuration."""
    if STORAGE_BACKEND == "s3":
        return S3Storage(
            endpoint_url=S3_ENDPOINT_URL,
            access_key=S3_ACCESS_KEY,
            secret_key=S3_SECRET_KEY,
            bucket=S3_BUCKET,
            prefix=S3_PREFIX,
            region=S3_REGION,
        )
    return LocalStorage()


storage = build_storage()

__all__ = ["storage", "build_storage", "LocalStorage", "S3Storage"]
