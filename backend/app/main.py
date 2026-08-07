"""FastAPI application: lifespan (DB + checkpointer + RAG rebuild), CORS, routers."""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from .agent.checkpointer import close_checkpointer, init_checkpointer
from .config import CORS_ORIGINS
from .database import init_db
from .rag.pipeline import rebuild_all
from .routers import admin, agents, auth, knowledge, public
from .services.health import collect_health


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    await init_checkpointer()
    # Reconcile pgvector indexes: only sources not yet indexed (or indexed
    # before pgvector) are re-fetched/re-embedded; the rest survive restarts.
    asyncio.create_task(rebuild_all())
    yield
    await close_checkpointer()


app = FastAPI(title="Agent-Plug API", version="0.1.0", lifespan=lifespan)


class PublicCorsMiddleware(BaseHTTPMiddleware):
    """Allow any origin for /api/public/* (widget endpoints use X-Agent-Token,
    not cookies, so wildcard CORS is safe)."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path.startswith("/api/public/"):
            origin = request.headers.get("origin")
            if request.method == "OPTIONS":
                response = Response(status_code=200)
            else:
                response = await call_next(request)
            if origin:
                response.headers["Access-Control-Allow-Origin"] = origin
            else:
                response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "*"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Max-Age"] = "86400"
            return response
        return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(PublicCorsMiddleware)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(agents.router)
app.include_router(knowledge.router)
app.include_router(public.router)


@app.get("/health")
async def health():
    """Liveness + third-party dependency checks (DB, storage/S3, OpenRouter).

    Overall status: `ok` (all up), `degraded` (DB up, a dependency down) or
    `down` (database unreachable). Each check carries its own status:
    `up` | `down` | `not_configured` (e.g. S3 when STORAGE_BACKEND=local,
    OpenRouter when OPENROUTER_API_KEY is missing).
    """
    return await collect_health()
