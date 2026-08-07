# AGENTS.md — backend (agent-plug)

FastAPI backend for Agent-Plug: RAG-powered AI agents embeddable on any website.
Read this file **before writing any backend code**. For repo-wide context also
read the root `AGENTS.md`.

## Stack
- Python 3.14, `uv` for deps/env
- FastAPI + uvicorn, SQLAlchemy 2 (async) + asyncpg, PostgreSQL
- LangChain `create_agent` (Deep Agents API) + `langchain-openrouter` (`ChatOpenRouter` — constructor kwarg is `model=`, NOT `model_name`)
- LangGraph `AsyncPostgresSaver` (checkpointer) for conversation state
- RAG: pgvector (PostgreSQL) via `langchain-postgres` `PGVector` — one collection `agent_{agent_id}` per agent — + custom `OpenRouterEmbeddings` (httpx → OpenRouter `/embeddings`), `RecursiveCharacterTextSplitter` (1000/200), `pypdf`, BeautifulSoup
- Auth: bcrypt + JWT (python-jose)

## Layout
```
backend/
  main.py                  # uvicorn entry: re-exports app.main:app
  pyproject.toml           # deps + [tool.pytest.ini_options] + [tool.pyright]
  .env                     # secrets/config (gitignored; copy .env.example)
  uploads/                 # uploaded PDFs (gitignored; created at runtime)
  app/
    config.py              # env config (.env at backend root); UPLOAD_DIR etc.
    database.py            # async engine/session, init_db (create_all + idempotent ALTERs)
    models.py              # User, Agent, Source (kind=url|pdf|text), AgentThread
    schemas.py             # pydantic request/response models
    auth.py                # bcrypt + JWT + get_current_user
    main.py                # FastAPI app, lifespan (DB + checkpointer + RAG rebuild), routers
    routers/
      auth.py              # /api/auth (register, login, me)
      agents.py            # /api/agents CRUD + embed + token rotation + avatar upload/remove
      public.py            # + GET /api/public/agents/{id}/avatar (serve WebP, no token)
      knowledge.py         # /api/agents/{id}/sources (+ /files, /text, /reindex)
      public.py            # /api/public (widget config/commands/stream/history + widget.js)
    services/
      agent_session_service.py  # background runs, SSE event buffer, sources event, marker parsing
      embed.py                  # embed snippet generation
      health.py                 # /health dependency checks (DB, storage/S3, OpenRouter)
    agent/
      agent.py             # build_agent (create_agent + middleware + RAG tool)
      tools.py             # search_knowledge_base tool + progress emitter
      checkpointer.py      # AsyncPostgresSaver lifecycle
    rag/
      embeddings.py        # OpenRouterEmbeddings (custom Embeddings impl, batched)
      fetcher.py           # URL fetch + BeautifulSoup HTML parsing (strip scripts/nav/footer)
      pdf.py               # pypdf text extraction (parse_pdf / parse_pdf_bytes)
      splitter.py          # RecursiveCharacterTextSplitter
      store.py             # RAGStoreManager (per-agent PGVector collection + chunk bookkeeping)
      pipeline.py          # index_source / reindex / rebuild_all (branch by source.kind)
    services/
      avatar.py            # Pillow: validate + compress uploads to WebP (max 512px, q82)
    storage/
      base.py              # Storage protocol (put/get/delete/exists)
      local.py             # LocalStorage — filesystem under UPLOAD_DIR (default)
      s3.py                # S3Storage — boto3, S3-compatible (SeaweedFS/MinIO/AWS)
      __init__.py          # `storage` singleton, dipilih dari STORAGE_BACKEND
    widget/widget.js       # self-contained embeddable widget (no deps, no build)
  tests/                   # pytest: unit + API integration (uses agent-plug-test DB)
```

## Commands
```sh
uv sync                          # install deps (uv add <pkg> / uv add --dev <pkg>)
uv run uvicorn app.main:app --port 8000   # dev server
uv run pytest -q                 # all backend tests (test DB: agent-plug-test)
uv run pyright main.py app/ tests/        # type-check — must be 0 errors before done
```

## Environment (.env)
`DATABASE_URL` (asyncpg; `VECTOR_DB_URL` untuk pgvector diturunkan otomatis
ke `postgresql+psycopg://` — override via env jika perlu), `SECRET_KEY`, `CORS_ORIGINS`, `OPENROUTER_API_KEY`,
`OPENROUTER_MODEL`, `OPENROUTER_BASE_URL`, `OPENROUTER_EMBEDDING_MODEL`,
`BACKEND_PUBLIC_URL`, `UPLOAD_DIR` (default `uploads/`), `UPLOAD_MAX_FILES=5`,
`UPLOAD_MAX_SIZE=10MB`, `INDEX_CONCURRENCY=3` (max sources indexed
concurrently server-wide; extra sources queue with status `pending` =
"Queued" in the dashboard — add endpoints return immediately via
`BackgroundTasks` and the 3s frontend poll tracks progress),
`PAGE_CONTEXT_MAX_CHARS=10000` (read_current_page tool truncation),
`ADMIN_EMAIL` + `ADMIN_PASSWORD` (platform admin — read-only monitoring; empty
= admin disabled). `DEFAULT_CHAT_PRESET` (default `platform`): the theme
preset baked into `chat_theme` at agent creation — MUST match a preset name
in `frontend/src/utils/themes.ts` AND `app/widget/widget.js` (both carry the
`platform` preset = the warm monochrome brand theme; the legacy `theme_color`
column is gone). Storage: `STORAGE_BACKEND` (`local`|`s3`),
`S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET`,
`S3_PREFIX`, `S3_REGION` (lihat `app/storage/`). Tests set `AP_TESTING=1` + a
`agent-plug-test` DB (see `tests/conftest.py`). Create both DBs:
`agent-plug` (dev) and `agent-plug-test` (pytest).

## Conventions & Rules
- **Modularity**: routers only validate + delegate; business logic lives in
  `services/`, `agent/`, `rag/`. New feature = model → schema → service/module
  → router → tests.
- **DB schema changes**: MVP has no alembic — `init_db()` runs `create_all` +
  idempotent `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` for new columns (see
  `database.py`). Always add the ALTER for existing dev DBs.
- **RAG vectors live in PostgreSQL (pgvector)**: chunks are stored by
  `langchain-postgres` `PGVector` in the `langchain_pg_collection` /
  `langchain_pg_embedding` tables (extension `vector` di-enable di
  `init_db()`), satu collection `agent_{agent_id}` per agent. On startup
  `rebuild_all()` (background task in lifespan) HANYA re-index source yang
  belum terindex di PG (`status != 'ready'` atau `chunk_ids IS NULL` —
  termasuk source peninggalan pra-pgvector); source siap tidak di-fetch/
  di-embed ulang karena vektornya persisten. Re-index manual
  `POST …/sources/reindex` tetap memaksa semua. Chunk ids persisted on
  `source.chunk_ids` (JSONB) so `DELETE …/sources/{id}` stays correct
  across restarts. Sources: `kind=url` (HTML fetch), `kind=pdf`
  (file stored in the storage backend — local disk under
  `uploads/{agent_id}/` atau S3/SeaweedFS — key `{agent_id}/{uuid}.pdf`,
  parsed with pypdf), `kind=text` (pasted text in `text_content` column).
  Every chunk carries `{url, title, source_id, agent_id}` metadata; `url` is
  `https://…`, `file://…`, or `text://…` — citations always resolve
  server-side, never from model-generated text.
- **Indexing queue**: source indexing is bounded by `INDEX_CONCURRENCY`
  (default 3) via a server-wide asyncio semaphore — sources wait in `pending`
  (dashboard "Queued") until a slot frees up, so bulk adds finish slower but
  never spike server/embedding load. The per-agent runner lock is unchanged:
  one drain loop per agent, new sources added mid-run get picked up.
- **Storage**: SEMUA akses file lewat `app.storage.storage` (singleton,
  `STORAGE_BACKEND=local|s3`) — jangan tulis langsung ke `UPLOAD_DIR` di
  router/pipeline. Key bersifat portable antar backend. Endpoint file:
  upload `POST .../sources/files` (PDF baru = source baru; hapus source lama
  manual via UI), delete `DELETE .../sources/{id}` (idempotent).
- **Agent avatar**: emoji ATAU foto (eksklusif). Upload `PUT
  /api/agents/{id}/avatar` — validasi FE+BE (GIF/JPEG/PNG/WebP, max
  `AVATAR_MAX_SIZE` 5MB), kompres Pillow ke WebP (`avatars/{id}.webp` di
  storage singleton, max `AVATAR_MAX_DIM` 512px, `AVATAR_QUALITY` 82), key
  tetap → URL stabil. **GIF animasi → WebP animasi** (cap
  `AVATAR_MAX_FRAMES` 200); **transparansi dipertahankan** (RGBA). Hapus
  `DELETE /api/agents/{id}/avatar` → kembali ke emoji. Serve publik tanpa
  token via `GET /api/public/agents/{id}/avatar` (dipakai `<img>` di widget;
  URL ada di `Agent.avatar_url`). Widget render foto dengan background
  transparan + `contain` (floating, tanpa warna dasar). Selama foto ada, FE
  men-disable emoji picker.
- **Chat threads**: semua chat (live widget DAN dashboard preview) berjalan
  lewat protocol public (`/api/public/*`) — preview meng-embed `widget.js`
  asli, jadi tidak ada route chat authed (`/api/threads` sudah dihapus).
  Thread key = `a{agent_id}:{thread_id}`, auth via header `X-Agent-Token`
  (agent.public_token).
- **/health**: liveness + third-party checks via `GET /health` (lihat
  `app/services/health.py`). Respon `{status: ok|degraded|down, checks:
  {database, storage, openrouter}, timestamp}`; tiap check punya status
  `up` | `down` | `not_configured` (contoh: S3 saat `STORAGE_BACKEND=local`,
  OpenRouter tanpa `OPENROUTER_API_KEY`). Cek berjalan konkuren, timeout 4s;
  DB `SELECT 1`, S3 `head_bucket`, OpenRouter GET `/models` (headers saja).
- **SSE event contract (stable)**: `lifecycle` (running/completed/cancelled/
  failed), `message_start`, `text_delta` (kind `text`|`reasoning`),
  `message_end` (usage), `sources` (exact `{url,title}` list parsed from tool
  outputs via `parse_source_markers`), `tool_start`, `tool_end`,
  `tool_progress`. Reasoning + tool events are ALWAYS streamed — show/hide is
  client-only. Keep-alive `: keepalive` every 30s.
- **Web-context tools (page fetching)**: two on-demand tools built on the
  existing `rag/fetcher.fetch_page`:
  - `read_current_page` (NO args): the widget sends `page_url` (default
    `window.location.href`; override via `data-page-url` attr; `"off"`
    disables) in every run.start input → stored on `AgentThread.page_url`.
    The URL comes from the thread the run executes on, never from the model.
  - `fetch_web_page(url)`: the MODEL chooses the URL (visitor asks about a
    page not in the KB). Input normalized (`https://` default for bare hosts)
    and rejected if not http(s).
  Both are SSRF-guarded (`_is_blocked_host`: private/loopback/link-local/
  reserved IPs refused — model-chosen URLs are untrusted), TTL-cached per URL
  (120s), truncated to `PAGE_CONTEXT_MAX_CHARS`, and their output uses a
  `[Source: …]` marker so the widget renders a citation chip. Tool-call caps
  (ToolCallLimitMiddleware, 5/run) bound abuse. Static pages only —
  JS-rendered SPAs return the HTML shell.
- **Admin console (read-only monitoring)**: the admin is a SPECIAL principal
  configured via env (`ADMIN_EMAIL`/`ADMIN_PASSWORD`), NOT a User row — login
  via `POST /api/admin/login` returns a JWT with `role="admin"` (`sub` =
  "admin", so regular user endpoints can never accept it). `app/routers/admin.py`
  is GET-only: `/stats` (platform totals + daily series), `/users` (searchable
  + paginated, per-user agent/request/token aggregates), `/users/{id}` (user +
  agents with source/usage stats), `/users/{id}/usage` (history across all of
  a user's agents, rows tagged with agent_name), `/agents/{id}` (agent +
  owner), `/agents/{id}/sources`, `/agents/{id}/usage`, `/agents/{id}/embed`
  (admin-scoped mirrors of the dashboard agent endpoints — the embed needs
  the public_token, which the admin legitimately holds). Frontend: `/admin` +
  `/admin/users/:id` + `/admin/agents/:id` (separate `useAdminStore`,
  localStorage key `ap_admin_token`, router meta `admin`/`adminGuest`).
  Everything is read-only — no admin mutation endpoints exist.
- **Usage rows record where the widget was called from**: every run writes an
  `agent_usage` row with the thread's `page_url` (the widget reports
  `window.location.href` per message; `record_usage` stores it). The Page
  column in the dashboard Usage tab and both admin usage tables shows the
  host + path and links out. Column added via the idempotent ALTER list
  (`agent_usage ADD COLUMN IF NOT EXISTS page_url`).
- **Widget parity**: the dashboard preview REUSES the real
  `app/widget/widget.js` (embedded via `PreviewTab.vue`, floating + auto-open
  on desktop through `data-auto-open`; live updates via the
  `window.__apwWidgets[agentId]` bridge — `setTheme`/`setOpts`/`destroy`).
  There is NO separate Vue chat rendering — keep it that way. Widget must stay
  dependency-free (validate with `node --check app/widget/widget.js`).
- **PREVIEW == LIVE (display config)**: chat theme + Show thinking/tools are
  stored on the Agent (`chat_theme`, `show_thinking`, `show_tools` — see
  `AgentPublicConfig`) and exposed to the widget via
  `GET /api/public/agents/{id}/config`. The dashboard preview is the ONLY
  place they can be adjusted; the widget has no settings UI. Changing the
  display-config contract means updating schema + `/config` + `widget.js`
  (`resolveTheme()`/`opts`/bridge) + `PreviewTab.vue` together.
- **Testing**: every endpoint/module gets tests in `tests/`. Conftest resets
  `agent-plug-test` at session start; use unique emails (`uuid4().hex`) so
  tests are idempotent. Chat tests inject a fake agent graph (see
  `test_chat_api.py`) and must close the checkpointer per test (loop affinity).
  Type-check with pyright must be clean.
