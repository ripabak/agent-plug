# Feature PRD: Knowledge Base (RAG Ingestion)

## 1. Feature Name
Knowledge base — URL ingestion & RAG indexing

## 2. Epic
- Epic PRD: `docs/ways-of-work/plan/agent-plug-mvp/epic.md`

## 3. Goal
**Problem:** The agent must answer from the customer's own content. Users need a dead-simple way to feed content: paste URLs, wait for indexing, done.
**Solution:** Per-agent source URLs stored in Postgres. A fetcher downloads each URL, parses HTML into clean text (with title), chunks it with `RecursiveCharacterTextSplitter`, embeds via OpenRouter embeddings (`perplexity/pplx-embed-v1-0.6b`), and stores chunks in a per-agent `InMemoryVectorStore` (LangChain). Every chunk carries `url` + `title` metadata so the agent can cite sources. On startup, indexes are rebuilt from stored sources.
**Impact:** Zero-setup knowledge base; users see live per-URL status; retrieval is grounded and citable.

## 4. User Personas
- Maker / Developer
- Business Owner

## 5. User Stories
- As a user, I want to add URLs to an agent so that its bot knows my content.
- As a user, I want to see indexing status per URL so that I know when it is ready.
- As a user, I want to remove or re-index a URL so that my bot stays up to date.
- As a visitor, I want the bot's answers to cite the source pages so that I can trust them.

## 6. Requirements
### Functional
- `POST /api/agents/{id}/sources` — body `{urls: [...]}`; creates Source rows (status `pending`), dedupes existing URLs; kicks off async indexing task.
- `GET /api/agents/{id}/sources` — list sources with status, title, error, chunk count, created/updated.
- `DELETE /api/agents/{id}/sources/{source_id}` — remove source + delete its chunks from the vector store.
- `POST /api/agents/{id}/sources/reindex` — re-fetch and re-index all (or failed) sources.
- Indexing pipeline per URL: `fetch (httpx) → parse (BeautifulSoup: title + text, strip script/style/nav/footer/header) → chunk (RecursiveCharacterTextSplitter 1000/200) → embed (OpenRouter) → add to InMemoryVectorStore with metadata {url, title, source_id}`.
- Store manager keyed by agent_id; `rebuild_all()` on startup re-embeds all stored sources (background).
### Non-Functional
- Non-blocking: indexing runs as background task; status polling.
- Resilient: per-URL try/except → status `failed` with error message.
- Embeddings called in batches (≤ 100 texts/request).
- Same URL deduped per agent.

## 7. Acceptance Criteria
- [ ] Adding URLs creates pending sources and starts indexing.
- [ ] Fetch+parse of a real HTML page produces non-empty text with correct title (unit test with fixture HTML).
- [ ] HTML parsing strips script/style/nav elements (unit test).
- [ ] Chunking splits long text into expected chunk count (unit test).
- [ ] Chunks in vector store carry `url` metadata (unit test with fake embeddings).
- [ ] Deleting a source removes its chunks (unit test).
- [ ] Failed URL ends with status `failed` + error, does not crash other URLs.
- [ ] `similarity_search` returns chunks whose metadata contains source URL (retrieval unit test).

## 8. Out of Scope
- PDF/docx/file upload, sitemap crawling, scheduled auto re-index, persistent vector DB.
