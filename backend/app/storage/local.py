"""Filesystem-backed storage (default backend).

Objects are stored as plain files under `UPLOAD_DIR`; keys are relative
paths like `{agent_id}/{uuid}.pdf` (same layout as before, so existing
uploads keep working).
"""

import asyncio
from pathlib import Path

from ..config import UPLOAD_DIR


class LocalStorage:
    """Stores objects as files under a root directory."""

    def __init__(self, root: str | Path = UPLOAD_DIR) -> None:
        self._root = Path(root)

    def _path_for(self, key: str) -> Path:
        root = self._root.resolve()
        path = (root / key).resolve()
        if not path.is_relative_to(root):
            raise ValueError(f"invalid storage key: {key!r}")
        return path

    async def put(self, key: str, data: bytes, content_type: str | None = None) -> None:
        def _write() -> None:
            path = self._path_for(key)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

        await asyncio.to_thread(_write)

    async def get(self, key: str) -> bytes:
        def _read() -> bytes:
            return self._path_for(key).read_bytes()

        return await asyncio.to_thread(_read)

    async def delete(self, key: str) -> None:
        def _delete() -> None:
            try:
                self._path_for(key).unlink()
            except FileNotFoundError:
                pass  # idempotent

        await asyncio.to_thread(_delete)

    async def exists(self, key: str) -> bool:
        return self._path_for(key).is_file()

    async def replace(self, key: str, data: bytes, content_type: str | None = None) -> None:
        await self.put(key, data, content_type)
