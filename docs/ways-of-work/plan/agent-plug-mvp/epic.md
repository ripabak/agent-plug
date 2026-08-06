# Epic: Agent-Plug MVP — RAG-Powered AI Agents Embeddable on Any Website

## 1. Epic Name

**Agent-Plug MVP** — "Plug a RAG-powered AI agent into any website with one snippet of HTML."

## 2. Goal

### Problem
Businesses want an AI assistant on their website that answers questions using **their own content** (docs, articles, product pages). Today this requires building a full chatbot stack: crawling content, chunking, embedding, retrieval, an agent runtime, and a chat widget. That is slow, expensive, and hard to maintain.

### Solution
Agent-Plug lets a user:
1. Create an AI agent in a dashboard.
2. Paste a list of URLs as the agent's knowledge base (RAG). The platform fetches, parses, chunks, and indexes that content automatically, storing the source URL on every chunk so answers can be cited.
3. Personalize the agent (name, description, system prompt, welcome message, theme).
4. Copy a single HTML snippet and paste it into any external website.
5. Visitors of that website see a floating chat button (bottom-right). Clicking it opens a chat panel where they can talk to the agent. Answers stream live over SSE.

### Impact
- Reduce time-to-first-chatbot from weeks to minutes.
- Increase website engagement / self-service deflection (fewer support tickets).
- Validate the "embed + RAG as a service" business model before building richer SDKs (React/Vue) and persistent vector stores.

## 3. User Personas

| Persona | Description | Needs |
|---|---|---|
| **Maker / Developer** | Wants a docs Q&A bot for their product website or open-source project. | Quick setup, embed snippet, test chat before deploying. |
| **Business Owner (non-technical)** | Wants a support bot for their store/service. | Paste URLs, watch indexing complete, copy-paste embed code. |
| **End Customer / Visitor** | A visitor on the customer's website chatting with the agent. | Fast answers, live streaming feel, clear tone. |

## 4. High-Level User Journeys

### Journey A — Create and configure an agent (dashboard)
1. User registers / logs in.
2. User clicks "Create Agent", enters a name, description, system prompt, welcome message, and theme.
3. User adds source URLs (one by one or pasted list).
4. User clicks "Index" and watches per-URL status go from `pending → fetching → indexing → ready` (or `failed`).
5. User previews the agent in a chat preview panel (SSE live).

### Journey B — Embed on a website
1. User opens the "Embed" tab.
2. User copies the generated HTML snippet (contains `data-agent-id` + `data-token` identifiers for auth).
3. User pastes it into their website HTML.
4. Visitors see a floating bot at bottom-right; clicking opens the chat.

### Journey C — Visitor chat (SSE)
1. Visitor opens chat panel, sees welcome message.
2. Visitor types a question.
3. Backend runs the agent; the agent calls the RAG retrieval tool; relevant chunks (with source URLs) are retrieved; answer streams token-by-token via SSE.
4. Visitor sees answer; optionally sees cited sources.

## 5. Business Requirements

### Functional Requirements
- **Auth**: register, login, JWT-based session; password hashing (bcrypt).
- **Agents**: CRUD agents; personalization (name, description, system prompt, welcome message, theme color, avatar emoji); each agent has a unique `public_token` used by the embed snippet.
- **Knowledge Base (RAG)**:
  - Add/remove source URLs per agent.
  - Fetch URL content, parse HTML to clean text (strip scripts/styles/nav), extract page title.
  - Chunk text (recursive splitting), embed with OpenRouter embeddings (`perplexity/pplx-embed-v1-0.6b`).
  - Store chunks in `InMemoryVectorStore` per agent (MVP), each chunk carrying `url` + `title` metadata.
  - Rebuild in-memory index on startup from stored sources.
  - Per-URL indexing status + retry/failure feedback.
- **Chat (SSE)**:
  - Dashboard preview chat (authenticated).
  - Public widget chat (authenticated by `public_token`).
  - Stream agent events: lifecycle, message tokens, tool start/end, citations.
  - Conversation state persisted via LangGraph checkpointer.
- **Embedding**:
  - Generate embed HTML snippet containing agent id + token.
  - Serve a static widget script that renders floating bot + chat panel and speaks SSE.
- **Frontend (Vue 3)**: login/register, dashboard with agent list, agent create/edit, knowledge base manager with live status, chat preview, embed code copy, demo page.

### Non-Functional Requirements
- **Modularity**: backend split into routers/services/agent/rag modules; frontend split into views/components/composables/stores.
- **Testability**: backend unit tests (pytest) mandatory; frontend unit tests (Vitest) using existing setup.
- **Security**: passwords hashed; JWT auth; `public_token` required for widget endpoints; CORS configured.
- **Performance**: streaming (SSE) for chat; no blocking on agent runs.
- **Usability**: MVP-minimal UI but with a clear, guided flow (create → configure → index → embed → test).
- **Documentation**: AGENTS.md in backend/ and frontend/.

## 6. Success Metrics

- Time from signup to working embedded widget < 15 minutes.
- RAG indexing success rate > 80% for well-formed URLs.
- Chat latency: first SSE token < 5s.
- 100% of backend unit tests and frontend unit tests pass.
- Answer always cites at least one source URL when knowledge is used.

## 7. Out of Scope

- Persistent vector store (only `InMemoryVectorStore` for MVP; index rebuilt on restart).
- React/Vue SDK widgets (only plain HTML `<script>` snippet for MVP).
- Multiple LLM providers per agent / model selection UI.
- Usage analytics / billing / quotas.
- File (PDF/docx) upload as RAG sources (URLs only).
- Conversation rating, admin panel, multi-tenancy teams.

## 8. Business Value

**Value: High** — Validates the core "embed + RAG as a service" value proposition end-to-end with minimal infrastructure (in-memory store, single backend). Every subsequent epic (persistent store, SDKs, billing) builds directly on this foundation.
