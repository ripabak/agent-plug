# Feature PRD: Agent Chat (SSE Runtime)

## 1. Feature Name
Agent chat runtime with SSE streaming

## 2. Epic
- Epic PRD: `docs/ways-of-work/plan/agent-plug-mvp/epic.md`

## 3. Goal
**Problem:** The widget and the dashboard preview both need a live chat experience backed by the RAG agent.
**Solution:** Reuse the reference `temps/backend` agent protocol: `POST .../commands` (run.start / run.cancel) then `POST .../stream` (SSE). The agent is built with `langchain.agents.create_agent` (Deep Agents API), `ChatOpenRouter` model (`qwen/qwen3.7-flash`), a RAG retrieval tool bound to the agent's vector store, and a LangGraph postgres checkpointer for conversation state. Events stream as SSE: lifecycle, text deltas, tool start/end.
**Impact:** Live token-by-token UX; conversation continuity; same endpoint shape as the proven reference project.

## 4. User Personas
- Maker / Developer (preview chat)
- End Customer / Visitor (widget chat)

## 5. User Stories
- As a dashboard user, I want to preview chat with my agent so that I can verify behavior before embedding.
- As a visitor, I want to ask questions and see streaming answers with cited sources.
- As a visitor, I want the conversation to persist across page refreshes (via thread id) so that I don't lose context.

## 6. Requirements
### Functional
- Authenticated preview: `POST /api/threads/{thread_id}/commands` (auth) and `POST /api/threads/{thread_id}/stream` (auth) with `input.agent_id` + `input.messages`.
- Public widget: `POST /api/public/agents/{agent_id}/commands` and `/stream` authenticated by `public_token` (header `X-Agent-Token`), `input.thread_id` optional.
- Commands: `run.start` (returns run_id), `run.cancel`.
- Events: `lifecycle` (running/completed/cancelled/failed), `message_start`, `text_delta` (kind text/reasoning), `message_end` (usage), `tool_start`, `tool_end`, `tool_progress`, `sources` (structured {url,title} list resolved from tool outputs).
- History: `GET .../{thread_id}` returns serialized messages (from checkpointer).
- Thread mapping stored in Postgres (`agent_thread`): thread_id, agent_id, user_id (nullable for public), thread_key namespaced by user or agent token.
- Agent prompt includes agent personalization (name, description, system prompt) + instruction that answers must cite source URLs from retrieved chunks when used.
- RAG tool: `search_knowledge_base(query)` → `vector_store.similarity_search(query, k=4)` → returns formatted chunks each prefixed with source URL + title; warns when nothing retrieved.
### Non-Functional
- Streaming response with `text/event-stream`, keep-alive every 30s, buffered history for late subscribers.
- Runs execute in background asyncio tasks so stream can reconnect (`since` param).
- Concurrency-safe per-thread event buffer with subscribers.

## 7. Acceptance Criteria
- [ ] `run.start` with valid agent_id returns run_id; with unknown/foreign agent returns error.
- [ ] SSE stream emits lifecycle + text_delta + message_end events (integration test with mocked model/tool).
- [ ] `run.cancel` stops a running task and emits `cancelled`.
- [ ] History endpoint returns previous messages after a completed run.
- [ ] Public endpoints reject requests without/invalid `public_token` (401).
- [ ] Retrieval tool returns chunk text + `[Source: {url}]` lines; unit tested with a fake store.

## 8. Out of Scope
- Multi-user rooms, moderation, streaming of rich content (images/files), usage billing.
