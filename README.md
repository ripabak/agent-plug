# Agent-Plug

AI-agent platform: users create RAG-powered AI agents, feed them knowledge
(URLs, PDFs, pasted text), and embed a floating chat widget on any website via
a single HTML snippet.

Monorepo with two independent projects:

| Project | Stack | Purpose |
|---|---|---|
| [`backend/`](backend/) | Python 3.14, uv, FastAPI, LangChain (Deep Agents), PostgreSQL | SSE chat runtime + RAG ingestion + public widget API |
| [`frontend/`](frontend/) | Node 22+, bun, Vue 3 + Vite + TS | dashboard: auth, agents, knowledge, preview, embed |

## Quickstart

### Docker (easiest — Postgres + backend + frontend in one command)

```sh
cp .env.example .env        # optional overrides (secrets come from backend/.env)
docker compose up --build
```

- Dashboard: http://localhost:5173
- API docs: http://localhost:8000/docs
- Widget: http://localhost:8000/api/public/widget.js

Semua konfigurasi (`OPENROUTER_API_KEY`, `SECRET_KEY`, …) diisi lewat file `.env`
di root repo (copy dari `.env.example`) — docker compose meng-interpolasinya
ke service. `backend/.env`/`frontend/.env` hanya untuk dev lokal.
Data persists di named volumes (`pgdata`, `uploads`).

### Local dev

Prereqs: PostgreSQL running locally, Python 3.14 (uv), Node 22+ (bun).

```sh
# 1. Backend (see backend/.env for DB + OpenRouter config)
cd backend
cp .env.example .env     # fill OPENROUTER_API_KEY etc.
uv sync
uv run uvicorn app.main:app --port 8000

# 2. Frontend (another terminal)
cd frontend
cp .env.example .env     # or just set VITE_API_BASE
bun install
bun dev
```

- Backend API: `http://localhost:8000` (docs at `/docs`)
- Frontend dashboard: `http://localhost:5173`
- Widget demo page: `http://localhost:5173/demo.html?agent=..&token=..&base=..`

## Repo layout

```
backend/
  main.py                  # uvicorn entry
  pyproject.toml           # deps (uv) — pyright/pytest config
  app/                     # FastAPI app: config, models, routers, services, agent, rag
  app/widget/widget.js     # self-contained embeddable widget (no deps, no build)
  tests/                   # pytest (unit + API integration)
frontend/
  src/                     # Vue SPA: api client, stores, views, components
  public/demo.html         # widget demo page
  package.json             # bun deps + scripts (dev/build/test/lint)
docs/                      # planning docs
docker-compose.yml         # db + backend + frontend (S3 eksternal opsional)
.env.example               # all env vars (backend / docker / frontend)
```

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
  `message_end`, `sources`, `tool_start`, `tool_end`, `tool_progress`.

## API Overview

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | /api/auth/register | – | register → token |
| POST | /api/auth/login | – | login → token |
| GET | /api/auth/me | Bearer | current user |
| POST/GET/PATCH/DELETE | /api/agents | Bearer | agent CRUD |
| POST | /api/agents/{id}/regenerate-token | Bearer | rotate public token |
| GET | /api/agents/{id}/embed | Bearer | embed snippet |
| POST/GET/DELETE | /api/agents/{id}/sources | Bearer | RAG source URLs + status |
| POST | /api/agents/{id}/sources/reindex | Bearer | re-index (all or failed) |
| POST | /api/threads/{t}/commands | Bearer | run.start / run.cancel |
| POST | /api/threads/{t}/stream | Bearer | SSE events |
| GET | /api/threads/{t} | Bearer | history |
| GET | /api/public/agents/{id}/config | X-Agent-Token | widget bootstrap |
| POST | /api/public/agents/{id}/commands | X-Agent-Token | widget run.start/cancel |
| POST | /api/public/agents/{id}/stream | X-Agent-Token | widget SSE |
| GET | /api/public/agents/{id}/history | X-Agent-Token | widget history |
| GET | /api/public/widget.js | – | widget script |

## Dashboard pages

| Route | Purpose |
|---|---|
| `/login`, `/register` | auth |
| `/dashboard` | agent list + create |
| `/agents/new` | guided create flow |
| `/agents/:id` | tabs: Configure / Knowledge / Preview / Embed |
| `/demo.html` | widget demo page (`?agent=..&token=..&base=..`) |

## Tests & checks (run before finishing)

| Project | Command |
|---|---|
| Backend tests | `cd backend && uv run pytest -q` |
| Backend type-check | `cd backend && uv run pyright main.py app/ tests/` |
| Frontend tests | `cd frontend && bun test:unit` |
| Frontend gates | `cd frontend && bun run type-check && bun lint && bun run build` |

## Environment variables

- [`backend/.env.example`](backend/.env.example) — backend config untuk dev
  lokal (`backend/.env`): DB URL, SECRET_KEY, OpenRouter keys, …
- [`.env.example`](.env.example) — config Docker Compose (root `.env`): semua
  variabel backend/db/frontend (termasuk `OPENROUTER_API_KEY`)
- [`frontend/.env.example`](frontend/.env.example) — frontend config untuk dev
  lokal (`frontend/.env`): `VITE_API_BASE`
