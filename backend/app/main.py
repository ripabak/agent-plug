"""FastAPI application: lifespan (DB + checkpointer + RAG rebuild), CORS, routers."""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .agent.checkpointer import close_checkpointer, init_checkpointer
from .config import CORS_ORIGINS
from .database import init_db
from .rag.pipeline import rebuild_all
from .routers import agents, auth, knowledge, public, threads


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    await init_checkpointer()
    # Rebuild in-memory RAG indexes from stored sources (MVP: in-memory store).
    asyncio.create_task(rebuild_all())
    yield
    await close_checkpointer()


app = FastAPI(title="Agent-Plug API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(agents.router)
app.include_router(knowledge.router)
app.include_router(threads.router)
app.include_router(public.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
