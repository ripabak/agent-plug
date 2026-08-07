"""Tests for the storage backends (LocalStorage + S3Storage)."""
import asyncio
from io import BytesIO

import pytest
from botocore.exceptions import ClientError

from app.storage.local import LocalStorage
from app.storage.s3 import S3Storage


class FakeS3Client:
    """Minimal in-memory stand-in for a boto3 S3 client."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.created_buckets: set[str] = set()

    def _key(self, kwargs: dict) -> str:
        return f"{kwargs['Bucket']}/{kwargs['Key']}"

    def create_bucket(self, **kwargs) -> None:
        self.created_buckets.add(kwargs["Bucket"])

    def put_object(self, **kwargs) -> None:
        self.objects[self._key(kwargs)] = kwargs["Body"]

    def get_object(self, **kwargs) -> dict:
        key = self._key(kwargs)
        if key not in self.objects:
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        return {"Body": BytesIO(self.objects[key])}

    def delete_object(self, **kwargs) -> None:
        self.objects.pop(self._key(kwargs), None)

    def head_object(self, **kwargs) -> dict:
        key = self._key(kwargs)
        if key not in self.objects:
            raise ClientError({"Error": {"Code": "404"}}, "HeadObject")
        return {}


@pytest.mark.asyncio
async def test_local_storage_roundtrip(tmp_path):
    s = LocalStorage(tmp_path)
    assert not await s.exists("a/b.txt")

    await s.put("a/b.txt", b"hello", content_type="text/plain")
    assert await s.exists("a/b.txt")
    assert (tmp_path / "a" / "b.txt").read_bytes() == b"hello"
    assert await s.get("a/b.txt") == b"hello"

    await s.put("a/b.txt", b"world")  # overwrite (same key)
    assert await s.get("a/b.txt") == b"world"

    await s.delete("a/b.txt")
    assert not await s.exists("a/b.txt")
    await s.delete("a/b.txt")  # idempotent


@pytest.mark.asyncio
async def test_local_storage_rejects_traversal(tmp_path):
    s = LocalStorage(tmp_path)
    with pytest.raises(ValueError):
        await s.put("../../etc/evil", b"x")
    with pytest.raises(ValueError):
        await s.get("../outside")


@pytest.mark.asyncio
async def test_s3_storage_roundtrip():
    client = FakeS3Client()
    s = S3Storage("http://seaweedfs:8333", "k", "s", "bucket", client=client)

    await s.put("doc/1.pdf", b"pdf-bytes", content_type="application/pdf")
    assert client.created_buckets == {"bucket"}  # lazy bucket creation
    assert await s.get("doc/1.pdf") == b"pdf-bytes"
    assert await s.exists("doc/1.pdf")

    await s.put("doc/1.pdf", b"new-bytes")  # overwrite (same key)
    assert await s.get("doc/1.pdf") == b"new-bytes"

    await s.delete("doc/1.pdf")
    assert not await s.exists("doc/1.pdf")
    await s.delete("doc/1.pdf")  # idempotent


@pytest.mark.asyncio
async def test_s3_storage_prefix():
    client = FakeS3Client()
    s = S3Storage("http://x", "k", "s", "bucket", prefix="agent-plug", client=client)

    await s.put("a.pdf", b"x")
    assert "bucket/agent-plug/a.pdf" in client.objects
    assert await s.get("a.pdf") == b"x"
    assert not await s.exists("other.pdf")

    await s.delete("a.pdf")
    assert "bucket/agent-plug/a.pdf" not in client.objects


@pytest.mark.asyncio
async def test_s3_storage_concurrent_first_writes_create_bucket_once():
    """Bucket creation is guarded by a lock — only one create_bucket call."""
    client = FakeS3Client()

    class CountingBucketClient(FakeS3Client):
        def __init__(self) -> None:
            super().__init__()
            self.create_calls = 0

        def create_bucket(self, **kwargs) -> None:
            self.create_calls += 1
            super().create_bucket(**kwargs)

    counting = CountingBucketClient()
    s = S3Storage("http://x", "k", "s", "bucket", client=counting)

    await asyncio.gather(*(s.put(f"f{i}.pdf", b"x") for i in range(10)))
    assert counting.create_calls == 1
    assert counting.created_buckets == {"bucket"}
    assert all(await asyncio.gather(*(s.exists(f"f{i}.pdf") for i in range(10))))
