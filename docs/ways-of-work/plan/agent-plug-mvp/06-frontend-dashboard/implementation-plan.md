# Implementation Plan: Frontend Dashboard

## Goal
Vue 3 (Vite + TS) SPA implementing the full product loop with minimal, UX-friendly design, reusing the existing Vitest setup.

## Requirements
- Auth (login/register), dashboard, agent detail with 4 tabs (Configure/Knowledge/Preview/Embed), demo page.
- Pinia stores, typed API client, SSE chat composable, polling for indexing status.

## Technical Considerations

### System Architecture Overview
```mermaid
graph TD
  subgraph Frontend (Vue 3 SPA)
    R1["router: login/register/dashboard/agents/:id"]
    S1["stores: auth, agents, sources, chat (Pinia)"]
    C1["api client (fetch wrapper)"]
    V1["views + tab components"]
    W1["sse composable (chat)"]
  end
  subgraph Backend API
    B1["/api/auth/*"]
    B2["/api/agents/*"]
    B3["/api/agents/{id}/sources*"]
    B4["/api/threads/* (SSE)"]
    B5["/api/agents/{id}/embed"]
  end
  R1 --> V1 --> C1 --> B1
  V1 --> S1 --> C1
  W1 --> B4
```
- **Stack**: Vue 3 `<script setup>` + TS, vue-router 4, pinia 3, vitest + @vue/test-utils (existing devDeps), plain CSS (design tokens in `src/assets/main.css`).
- **API client**: `src/api/client.ts` — `apiFetch(path, {method, body})` adds `Authorization` from auth store; error → normalized `{message}`; 401 → logout redirect.
- **SSE chat composable** `src/composables/useAgentChat.ts`: state machine (idle/running/completed/failed), `run(messages)`, parser shared shape with widget; used by PreviewTab.
- **Guided create flow**: Dashboard "New Agent" → `AgentCreateView` (single form: name, description, welcome message, theme) → on success navigate to detail Knowledge tab with a small "next steps" banner (configure → add URLs → preview → embed).

### Components & Views
| Path | Purpose |
|---|---|
| `src/views/LoginView.vue`, `RegisterView.vue` | auth forms |
| `src/views/DashboardView.vue` | agent cards + create |
| `src/views/AgentCreateView.vue` | create form |
| `src/views/AgentDetailView.vue` | tabs shell |
| `src/components/ConfigureTab.vue` | personalization form (auto-save button) |
| `src/components/KnowledgeTab.vue` | URL textarea + list + status + poll |
| `src/components/PreviewTab.vue` | SSE chat preview |
| `src/components/EmbedTab.vue` | snippet + copy + demo link + token |
| `src/components/ChatPanel.vue` | reusable chat UI (messages/streaming/tool/sources) |
| `src/components/StatusBadge.vue` | source status badge |
| `src/public/demo.html` | widget demo page (in `frontend/public/`) |

### Data / State
- `auth`: `{token, user}` persisted to localStorage; `bootstrap()` calls `/me` on app load.
- `sources`: polling every 3s in KnowledgeTab while any status ∈ {pending, fetching, indexing}.
- `chat`: per-agent thread id in sessionStorage; messages list; streaming delta accumulation.

## Testing (existing Vitest setup)
- `src/api/__tests__/client.spec.ts` — mocked fetch: auth header, 401 handling, error normalization.
- `src/stores/__tests__/auth.spec.ts` — login/register/logout/restore.
- `src/composables/__tests__/useAgentChat.spec.ts` — SSE event parsing + state transitions (mocked fetch).
- `src/components/__tests__/StatusBadge.spec.ts` / `LoginView.spec.ts` — component rendering & form submit.
- Gates: `bun test:unit`, `bun run type-check`, `bun run build`.

## Key Files
- `frontend/src/main.ts`, `router/index.ts`, `stores/*.ts`, `api/client.ts`, `composables/useAgentChat.ts`
- `frontend/src/views/*.vue`, `frontend/src/components/*.vue`
