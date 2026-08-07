"""S3-compatible object storage backend (SeaweedFS / MinIO / AWS S3).

Uses path-style addressing + SigV4 (required by SeaweedFS and MinIO). The
bucket is created lazily on the first write. `client` can be injected in
tests to avoid real network I/O.
"""

import asyncio
from typing import Any

from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import ClientError


class S3Storage:
    """boto3-backed storage for any S3-compatible endpoint."""

    def __init__(
        self,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        prefix: str = "",
        region: str = "us-east-1",
        client: Any | None = None,
    ) -> None:
        self._bucket = bucket
        self._prefix = f"{prefix.rstrip('/')}/" if prefix else ""
        self._client: BaseClient = client or _make_client(
            endpoint_url, access_key, secret_key, region
        )
        self._bucket_lock = asyncio.Lock()
        self._bucket_ready = False

    # --- internals ---

    def _object_key(self, key: str) -> str:
        return f"{self._prefix}{key}"

    async def _ensure_bucket(self) -> None:
        """Create the bucket once, lazily, on first write (SeaweedFS/MinIO)."""
        if self._bucket_ready:
            return
        async with self._bucket_lock:
            if self._bucket_ready:
                return

            def _create() -> None:
                try:
                    self._client.create_bucket(Bucket=self._bucket)
                except ClientError as exc:
                    code = exc.response.get("Error", {}).get("Code", "")
                    # Already-owned / already-exists is fine; anything else propagates.
                    if code not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists", "409"):
                        raise

            await asyncio.to_thread(_create)
            self._bucket_ready = True

    # --- Storage interface ---

    async def put(self, key: str, data: bytes, content_type: str | None = None) -> None:
        await self._ensure_bucket()

        def _put() -> None:
            kwargs: dict[str, Any] = {
                "Bucket": self._bucket,
                "Key": self._object_key(key),
                "Body": data,
            }
            if content_type:
                kwargs["ContentType"] = content_type
            self._client.put_object(**kwargs)

        await asyncio.to_thread(_put)

    async def get(self, key: str) -> bytes:
        def _get() -> bytes:
            obj = self._client.get_object(Bucket=self._bucket, Key=self._object_key(key))
            return obj["Body"].read()

        return await asyncio.to_thread(_get)

    async def delete(self, key: str) -> None:
        def _delete() -> None:
            try:
                self._client.delete_object(Bucket=self._bucket, Key=self._object_key(key))
            except ClientError:
                pass  # idempotent

        await asyncio.to_thread(_delete)

    async def exists(self, key: str) -> bool:
        def _head() -> bool:
            try:
                self._client.head_object(Bucket=self._bucket, Key=self._object_key(key))
                return True
            except ClientError:
                return False

        return await asyncio.to_thread(_head)

    async def replace(self, key: str, data: bytes, content_type: str | None = None) -> None:
        await self.put(key, data, content_type)


def _make_client(endpoint_url: str, access_key: str, secret_key: str, region: str) -> BaseClient:
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url or None,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
        config=Config(
            s3={"addressing_style": "path"},
            signature_version="s3v4",
            retries={"max_attempts": 3, "mode": "standard"},
        ),
    )
