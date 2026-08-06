# AGENTS.md — backend (agent-plug)

FastAPI backend for Agent-Plug: RAG-powered AI agents embeddable on any website.
Read this file **before writing any backend code**. For repo-wide context also
read the root `AGENTS.md`.

## Stack
- Python 3.14, `uv` for deps/env
- FastAPI + uvicorn, SQLAlchemy 2 (async) + asyncpg, PostgreSQL
- LangChain `create_agent` (Deep Agents API) + `langchain-openrouter` (`ChatOpenRouter` — constructor kwarg is `model=`, NOT `model_name`)
- LangGraph `AsyncPostgresSaver` (checkpointer) for conversation state
- RAG: `InMemoryVectorStore` per agent + custom `OpenRouterEmbeddings` (httpx → OpenRouter `/embeddings`), `RecursiveCharacterTextSplitter` (1000/200), `pypdf`, BeautifulSoup
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
      agents.py            # /api/agents CRUD + embed + token rotation
      knowledge.py         # /api/agents/{id}/sources (+ /files, /text, /reindex)
      threads.py           # /api/threads (authed SSE chat)
      public.py            # /api/public (widget config/commands/stream/history + widget.js)
    services/
      agent_session_service.py  # background runs, SSE event buffer, sources event, marker parsing
      embed.py                  # embed snippet generation
    agent/
      agent.py             # build_agent (create_agent + middleware + RAG tool)
      tools.py             # search_knowledge_base tool + progress emitter
      checkpointer.py      # AsyncPostgresSaver lifecycle
    rag/
      embeddings.py        # OpenRouterEmbeddings (custom Embeddings impl, batched)
      fetcher.py           # URL fetch + BeautifulSoup HTML parsing (strip scripts/nav/footer)
      pdf.py               # pypdf text extraction for uploaded PDFs
      splitter.py          # RecursiveCharacterTextSplitter
      store.py             # RAGStoreManager (per-agent InMemoryVectorStore + chunk bookkeeping)
      pipeline.py          # index_source / reindex / rebuild_all (branch by source.kind)
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
`DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`, `OPENROUTER_API_KEY`,
`OPENROUTER_MODEL`, `OPENROUTER_BASE_URL`, `OPENROUTER_EMBEDDING_MODEL`,
`BACKEND_PUBLIC_URL`, `UPLOAD_DIR` (default `uploads/`), `UPLOAD_MAX_FILES=5`,
`UPLOAD_MAX_SIZE=10MB`. Tests set `AP_TESTING=1` + a `agent-plug-test` DB
(see `tests/conftest.py`). Create both DBs: `agent-plug` (dev) and
`agent-plug-test` (pytest).

## Conventions & Rules
- **Modularity**: routers only validate + delegate; business logic lives in
  `services/`, `agent/`, `rag/`. New feature = model → schema → service/module
  → router → tests.
- **DB schema changes**: MVP has no alembic — `init_db()` runs `create_all` +
  idempotent `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` for new columns (see
  `database.py`). Always add the ALTER for existing dev DBs.
- **RAG stores are in-memory**: on startup `rebuild_all()` re-indexes from the
  `source` rows (background task in lifespan). Sources: `kind=url` (HTML
  fetch), `kind=pdf` (file under `uploads/{agent_id}/`, parsed with pypdf),
  `kind=text` (pasted text in `text_content` column). Every chunk carries
  `{url, title, source_id, agent_id}` metadata; `url` is `https://…`,
  `file://…`, or `text://…` — citations always resolve server-side, never from
  model-generated text.
- **Chat threads**: dashboard = `u{user_id}:{thread_id}`, widget =
  `a{agent_id}:{thread_id}`. Public endpoints authenticate with the
  `X-Agent-Token` header (agent.public_token).
- **SSE event contract (stable)**: `lifecycle` (running/completed/cancelled/
  failed), `message_start`, `text_delta` (kind `text`|`reasoning`),
  `message_end` (usage), `sources` (exact `{url,title}` list parsed from tool
  outputs via `parse_source_markers`), `tool_start`, `tool_end`,
  `tool_progress`. Reasoning + tool events are ALWAYS streamed — show/hide is
  client-only. Keep-alive `: keepalive` every 30s.
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
