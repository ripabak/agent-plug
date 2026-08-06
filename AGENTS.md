# agent-plug

Monorepo: an AI-agent platform where users create RAG-powered AI agents, feed
them knowledge (URLs, PDFs, pasted text), and embed a floating chat widget on
any website via a single HTML snippet.

This monorepo contains **two independent projects**:

- `backend/` — FastAPI + LangChain (Deep Agents) + SSE chat runtime + RAG ingestion
- `frontend/` — Vue 3 + Vite + TS dashboard (auth, agents, knowledge, preview, embed)

---

## ⚠️ MANDATORY — READ BEFORE DEVELOPING

**Every time you work on code in this repo, you MUST first read the AGENTS.md
of the project you are touching, and follow its commands, layout, and
conventions.**

- Backend work (Python/FastAPI/RAG): read **`backend/AGENTS.md`**
- Frontend work (Vue/TS/dashboard): read **`frontend/AGENTS.md`**
- Both files define the exact commands, module layout, test requirements,
  and conventions that have proven to work in this codebase. Do not invent
  parallel workflows — reuse what is documented there.

When a change spans both projects (e.g. an API contract, an SSE event, the
chat widget), read **both** AGENTS.md files and keep the two sides consistent
(backend emits, frontend consumes, `app/widget/widget.js` mirrors the preview).

---

## Quick start

```sh
# Prereqs: PostgreSQL running locally, Python 3.14 (uv), Node 22+ (bun)

# 1. Backend (see backend/.env for DB + OpenRouter config)
cd backend
uv sync
uv run uvicorn app.main:app --port 8000

# 2. Frontend (in another terminal)
cd frontend
bun install
bun dev
```

- Backend API: `http://localhost:8000` (docs at `/docs`)
- Frontend dashboard: `http://localhost:5173`
- Widget demo page: `http://localhost:5173/demo.html?agent=..&token=..&base=..`

## Tests & checks (always run before finishing)

| Project | Command |
|---|---|
| Backend tests | `cd backend && uv run pytest -q` |
| Backend type-check | `cd backend && uv run pyright main.py app/ tests/` |
| Frontend tests | `cd frontend && bun test:unit` |
| Frontend gates | `cd frontend && bun run type-check && bun lint && bun run build` |

## Key concepts

- **Agent** — user-scoped AI assistant with personalization (name, prompt,
  welcome message, theme, avatar) and a `public_token` for widget auth.
- **Source** — one knowledge input per agent: `kind=url` (web page),
  `kind=pdf` (uploaded file), or `kind=text` (pasted long text). Indexed into
  a per-agent `InMemoryVectorStore` (rebuilt on startup).
- **Thread** — a conversation; dashboard = `u{user_id}:{thread_id}`,
  widget = `a{agent_id}:{thread_id}`.
- **Embed snippet** — `<script data-agent-id data-token data-base-url>` served
  by the backend; `data-token` (public_token) authenticates the public widget
  endpoints (`X-Agent-Token` header).
- **SSE events** — `lifecycle`, `message_start`, `text_delta` (text|reasoning),
  `message_end`, `sources`, `tool_start`, `tool_end`, `tool_progress`. Reasoning
  and tool events are always streamed; showing/hiding them is a client option.
