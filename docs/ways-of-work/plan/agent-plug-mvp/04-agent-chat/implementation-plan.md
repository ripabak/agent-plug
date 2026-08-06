# Implementation Plan: Agent Chat (SSE Runtime)

## Goal
SSE-based chat runtime for dashboard preview (authenticated) and widget (token-authenticated), reusing the proven agent protocol from `temps/backend` (`commands` + `stream`), built with LangChain Deep Agents API and a RAG retrieval tool.

## Requirements
- `POST .../commands` (`run.start` returns run_id, `run.cancel`), `POST .../stream` SSE, `GET .../{thread_id}` history.
- Agent = `create_agent(model=ChatOpenRouter(...), tools=[search_knowledge_base], system_prompt=personalized, checkpointer=AsyncPostgresSaver, middleware=[Summarization, ClearToolUsesEdit])`.
- Thread mapping in Postgres; event buffer + subscribers for reconnect (`since`).

## Technical Considerations

### System Architecture Overview
```mermaid
graph TD
  subgraph API Layer
    C1["POST /api/threads/{t}/commands (auth)"]
    C2["POST /api/threads/{t}/stream (auth)"]
    C3["POST /api/public/agents/{id}/commands (X-Agent-Token)"]
    C4["POST /api/public/agents/{id}/stream (X-Agent-Token)"]
    C5["GET .../{t} history"]
  end
  subgraph Runtime Layer (services/agent_session_service.py)
    M1["SessionManager: AgentSession buffers + subscribers"]
    M2["start_agent_run: astream_events v3 → SSE events"]
  end
  subgraph Agent Layer (agent/)
    A1["agent.py: build_agent(create_agent + middleware)"]
    A2["tools.py: search_knowledge_base (RAG store)"]
  end
  subgraph Persistence
    P1["agent_thread table (Postgres)"]
    P2["AsyncPostgresSaver (checkpoint)"]
  end
  subgraph External
    X1["openrouter.ai chat completions (ChatOpenRouter)"]
  end
  C1 --> M2 --> A1 --> X1
  A1 --> A2 --> RAG
  M2 --> P2
  M1 --> C2
  A1 --> P1
```
- **Stack choice**: mirror `temps/backend` (`langchain.agents.create_agent`, `ChatOpenRouter`, `AsyncPostgresSaver`, middleware `SummarizationMiddleware`/`ContextEditingMiddleware`/`ClearToolUsesEdit`), plus our RAG tool.
- **Thread key namespacing**: authenticated → `"u{user_id}:{thread_id}"`; public → `"a{agent_id}:{thread_id}"` so users can't collide.
- **Event contract** (SSE `event:` = method): `lifecycle`{running/completed/cancelled/failed}, `message_start`, `text_delta`{kind: text|reasoning}, `message_end`{usage}, `tool_start`, `tool_end`, `tool_progress`, `sources`{id, sources:[{url,title}]} (exact URLs from tool outputs). Keep-alive `: keepalive` every 30s.
- **History**: serialize checkpointer state messages (`serialize_message` from reference).

### Database Schema Design
```mermaid
erDiagram
  "agent_thread" {
    int id PK
    string thread_id UK  "namespaced key"
    int agent_id FK
    int user_id FK nullable "null for public widget"
    datetime created_at
    datetime updated_at
  }
  "user" ||--o{ "agent_thread" : has
  "agent" ||--o{ "agent_thread" : has
```
- Checkpoint state lives in LangGraph checkpointer tables (auto-created); `agent_thread` only maps key→agent/user.

### API Design
| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | /api/threads/{t}/commands | Bearer | input `{agent_id, messages}`; validates agent ownership |
| POST | /api/threads/{t}/stream | Bearer | `{channels, since}` |
| GET | /api/threads/{t} | Bearer | history |
| DELETE | /api/threads/{t} | Bearer | delete state + mapping |
| POST | /api/public/agents/{id}/commands | X-Agent-Token | input `{thread_id?, messages}` |
| POST | /api/public/agents/{id}/stream | X-Agent-Token | `{channels, since}` |
| GET | /api/public/agents/{id}/config | X-Agent-Token | widget bootstrap data |

### Security & Performance
- Public endpoints validate `public_token` against agent row (401 on mismatch/rotation).
- Streaming runs in background task; subscriber queues with timeout → keepalive; cancellation via task.cancel().
- Model: `qwen/qwen3.7-flash`, temperature 0.3, max_tokens 8192, reasoning effort low (reference parity).

## Key Files
- `backend/app/agent/agent.py`, `tools.py`, `checkpointer.py`
- `backend/app/services/agent_session_service.py`
- `backend/app/routers/threads.py`, `public.py`
- `backend/tests/test_agent_session.py`, `test_tools.py`
