"""Health checks for third-party dependencies (DB, storage/S3, OpenRouter).

Each check runs concurrently with a short timeout and returns a small dict:
    {"status": "up" | "down" | "not_configured", ...details}

- database: real `SELECT 1` on the app's async engine (critical).
- storage: for `STORAGE_BACKEND=s3` a cheap bucket probe (head_bucket); for
  `local` it reports the filesystem backend as up (nothing external).
- openrouter: lightweight GET to the base URL's `/models` (headers only, the
  body is not downloaded). Without an API key it reports `not_configured`.
"""
import asyncio
import time
from typing import cast

import httpx
from sqlalchemy import text

from ..config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_EMBEDDING_MODEL,
    STORAGE_BACKEND,
    UPLOAD_DIR,
)
from ..database import engine
from ..storage import S3Storage, storage

CHECK_TIMEOUT = 4.0  # seconds per check (they run concurrently)


def _ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)


async def _check_database() -> dict:
    start = time.monotonic()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "up", "latency_ms": _ms(start)}
    except Exception as exc:  # noqa: BLE001 - health endpoint reports any failure
        return {"status": "down", "error": str(exc)[:200]}


async def _check_storage() -> dict:
    if STORAGE_BACKEND != "s3":
        return {
            "backend": "local",
            "status": "up",
            "note": f"filesystem under {UPLOAD_DIR}",
        }
    start = time.monotonic()
    s3 = cast(S3Storage, storage)  # guarded by STORAGE_BACKEND check above
    try:
        def _probe() -> None:
            from botocore.exceptions import ClientError

            try:
                s3._client.head_bucket(Bucket=s3._bucket)
            except ClientError as exc:
                code = exc.response.get("Error", {}).get("Code", "")
                # Bucket missing = endpoint reachable (it is created lazily on
                # first write), so that still counts as up.
                if code in ("404", "NoSuchBucket"):
                    return
                raise

        await asyncio.wait_for(asyncio.to_thread(_probe), CHECK_TIMEOUT)
        return {"backend": "s3", "status": "up", "latency_ms": _ms(start)}
    except Exception as exc:  # noqa: BLE001
        return {"backend": "s3", "status": "down", "error": str(exc)[:200]}


async def _check_openrouter() -> dict:
    if not OPENROUTER_API_KEY:
        return {
            "status": "not_configured",
            "note": "OPENROUTER_API_KEY is not set",
        }
    start = time.monotonic()
    try:
        url = f"{OPENROUTER_BASE_URL.rstrip('/')}/models"
        # stream + close without reading the body: only headers are needed.
        async with httpx.AsyncClient(timeout=CHECK_TIMEOUT) as client:
            async with client.stream(
                "GET",
                url,
                headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            ) as resp:
                status = resp.status_code
        latency = _ms(start)
        if status == 200:
            return {
                "status": "up",
                "latency_ms": latency,
                "embedding_model": OPENROUTER_EMBEDDING_MODEL,
            }
        if status in (401, 403):
            return {
                "status": "down",
                "error": f"HTTP {status} — invalid API key",
                "latency_ms": latency,
            }
        return {"status": "down", "error": f"HTTP {status}", "latency_ms": latency}
    except Exception as exc:  # noqa: BLE001
        return {"status": "down", "error": str(exc)[:200]}


async def collect_health() -> dict:
    """Run all checks concurrently and aggregate the overall status."""
    db, storage_check, openrouter = await asyncio.gather(
        _check_database(), _check_storage(), _check_openrouter()
    )
    checks = {
        "database": db,
        "storage": storage_check,
        "openrouter": openrouter,
    }
    if checks["database"]["status"] != "up":
        status = "down"
    elif any(c["status"] == "down" for c in checks.values()):
        status = "degraded"
    else:
        status = "ok"
    return {"status": status, "checks": checks, "timestamp": _iso_now()}


def _iso_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds")
