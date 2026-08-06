# Issues Checklist: Agent-Plug MVP

> Implementation tracking — status: **COMPLETE (MVP delivered & verified)**.
> Execution order: Auth → Agents → Knowledge → Chat → Widget → Frontend → Verify.

## Feature 1: Authentication

- [x] Backend scaffolding (pyproject, .env, config, database, models, main) — `backend/app/{config,database,models,schemas,auth}.py`, `app/main.py`
- [x] Auth service: hash/verify password, JWT create/decode, get_current_user — `backend/app/auth.py`
- [x] Auth routes: register/login/me — `backend/app/routers/auth.py`
- [x] Auth tests (12) — `backend/tests/test_auth.py`

## Feature 2: Agent Management

- [x] Agent + Source models — `backend/app/models.py`
- [x] Agents routes: CRUD, regenerate-token, embed — `backend/app/routers/agents.py`
- [x] Ownership checks (404 for foreign agents) — `backend/app/routers/agents.py`
- [x] Agent + embed tests — `backend/tests/test_agents.py`, `test_embed.py`

## Feature 3: Knowledge Base (RAG)

- [x] OpenRouterEmbeddings (custom Embeddings impl, batched) — `backend/app/rag/embeddings.py`
- [x] HTML fetcher/parser (BeautifulSoup, strips script/nav/footer, title) — `backend/app/rag/fetcher.py`
- [x] Chunking (RecursiveCharacterTextSplitter 1000/200) — `backend/app/rag/splitter.py`
- [x] RAGStoreManager (per-agent InMemoryVectorStore + source chunk bookkeeping) — `backend/app/rag/store.py`
- [x] Indexing pipeline + startup rebuild — `backend/app/rag/pipeline.py`
- [x] Sources routes: add/list/delete/reindex + status — `backend/app/routers/knowledge.py`
- [x] RAG tests (fetcher, store, tools, pipeline) — `backend/tests/test_fetcher.py`, `test_store.py`, `test_tools.py`, `test_pipeline.py`
- [x] **PDF upload (kind=pdf)**: `POST /api/agents/{id}/sources/files` (multipart, ≤5 files, ≤10MB, `.pdf` only); files stored under `uploads/{agent_id}/`; pipeline branches `url → fetch_page` / `pdf → parse_pdf` (pypdf); delete removes the file; idempotent ALTERs in `init_db()` — `backend/app/rag/pdf.py`, `rag/pipeline.py`, `routers/knowledge.py`, `models.py`, `schemas.py`, `config.py` (UPLOAD_DIR)
- [x] PDF tests — `backend/tests/test_pdf.py` (crafted valid PDF), `test_knowledge.py` (upload API: success/422/delete-removes-file), `test_sources.py` (file:// citation markers)
- [x] **Long text source (kind=text)**: `POST /api/agents/{id}/sources/text` (`{title?, content}` 10..200k chars); stored in `text_content` column; pipeline `kind=text → text_content` directly (no fetch/file); markers accept `text://` and render as 📝 label — `backend/app/models.py`, `schemas.py`, `rag/pipeline.py`, `routers/knowledge.py`, `services/agent_session_service.py`
- [x] Text tests — `test_knowledge.py` (API: create/422), `test_pdf.py` (index text end-to-end), `test_sources.py` (text:// markers); frontend `client.spec.ts`, `sse.spec.ts`
- [x] Frontend Knowledge tab: 3-mode input switcher (🌐 URLs / 📄 PDF / 📝 Text) — `frontend/src/components/KnowledgeTab.vue`, `assets/main.css` (.source-modes)

## Feature 4: Agent Chat (SSE)

- [x] LangGraph AsyncPostgresSaver lifecycle — `backend/app/agent/checkpointer.py`
- [x] Agent builder (create_agent + middleware + personalized prompt) — `backend/app/agent/agent.py`
- [x] RAG retrieval tool (citations with source URLs) — `backend/app/agent/tools.py`
- [x] Session service (background runs, event buffer, subscribers, run.start/cancel) — `backend/app/services/agent_session_service.py`
- [x] Threads routes (authed) + public routes (X-Agent-Token) + widget config — `backend/app/routers/threads.py`, `routers/public.py`
- [x] Chat tests (commands, auth, SSE event contract via stream_events) — `backend/tests/test_chat_api.py`

## Feature 5: Embeddable Widget

- [x] widget.js — dependency-free floating bot + SSE chat + citations — `backend/app/widget/widget.js`
- [x] Widget serving (GET /api/public/widget.js) — `backend/app/routers/public.py`
- [x] Embed snippet generation — `backend/app/services/embed.py`
- [x] Widget contract tests — `backend/tests/test_embed.py`

## Feature 6: Frontend Dashboard

- [x] App shell: router (auth guard), pinia stores, typed api client — `frontend/src/router/`, `stores/`, `api/`
- [x] SSE utils (parseSseFrame, readSseStream, extractSources) — `frontend/src/utils/sse.ts`
- [x] Auth views — `frontend/src/views/LoginView.vue`, `RegisterView.vue`
- [x] Dashboard + guided create — `DashboardView.vue`, `AgentCreateView.vue`
- [x] Agent detail tabs: Configure / Knowledge (live status polling + **PDF upload zone**) / Preview (SSE) / Embed — `frontend/src/components/*.vue`
- [x] Demo page — `frontend/public/demo.html`
- [x] Frontend tests (32) — `src/**/__tests__/*.spec.ts` (incl. upload API client, file:// sources)

## Verification (DoD)

- [x] Backend: `uv run pytest -q` → 66 passed
- [x] Frontend: `bun test:unit` → 34 passed
- [x] Frontend: `bun run type-check` + `bun run build` → pass
- [x] Frontend: `bun lint` → pass (oxlint + eslint)
- [x] E2E verified: register → create agent → add URL → index (32 chunks ready) → widget config → embed snippet → real SSE chat (1394 events, grounded answer with `[Source: ...]` citation) → demo page served
- [x] **Citation reliability fix**: LLM sometimes regenerated/mangled source URLs in its answer text. Now the backend emits a structured `sources` SSE event (exact URLs resolved from tool outputs) + prompt instructs numbered citations without URLs + URL sanitization in widget/frontend/backend (`parse_source_markers`, `isValidHttpUrl`). Verified with the real blog agent: `sources` event carries clean URLs, answer text has no mangled URLs.
- [x] **UI parity fix (preview == demo widget)**: welcome message now shown in the preview (was widget-only); thinking (reasoning) rendered as a collapsible block; tool calls rendered as status chips (running/success/error); a ⚙ display menu (Show thinking / Show tools) in both preview & widget, persisted per client. Reasoning + tool events are always streamed by the backend (`text_delta` kind=reasoning, `tool_start/end/progress`) — the toggle only hides/shows them client-side. Preview header is now themed exactly like the widget (avatar, name, description, gear menu). Verified: real chat streamed 232 reasoning + 20 text deltas.
- [x] **Bug fix**: `reset_progress_emitter` was called but not defined in `app/agent/tools.py` (silent NameError in the background run task). Added it and cleaned up the emitter lifecycle in `agent_session_service.py`; backend log verified error-free.
- [x] AGENTS.md added to backend/, frontend/, and root
- [x] .env fixed (embedding model typo), .env.example added, READMEs updated
