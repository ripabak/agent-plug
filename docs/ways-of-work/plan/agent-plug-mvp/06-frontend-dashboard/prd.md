# Feature PRD: Frontend Dashboard (Vue 3)

## 1. Feature Name
Frontend dashboard — auth, agent management, knowledge base, preview, embed

## 2. Epic
- Epic PRD: `docs/ways-of-work/plan/agent-plug-mvp/epic.md`

## 3. Goal
**Problem:** Users need a friendly UI to perform the whole flow: sign up, create an agent, feed URLs, wait for indexing, preview chat, and copy the embed snippet.
**Solution:** A minimal but UX-friendly Vue 3 SPA (Vite + TS + Pinia + Vue Router) with pages: Login, Register, Dashboard (agent list), Agent Detail (tabs: Configure / Knowledge / Preview / Embed). A guided "Create Agent" flow with a stepper-like experience.
**Impact:** The full product loop is usable in < 15 minutes; existing Vitest setup is reused.

## 4. User Personas
- Maker / Developer
- Business Owner

## 5. User Stories
- As a visitor, I want to register/login so that I can reach my dashboard.
- As a user, I want a guided create flow (agent info → knowledge URLs → preview → embed) so that I don't get lost.
- As a user, I want live indexing status so that I know when the bot is ready.
- As a user, I want to chat-preview via SSE so that I can test before embedding.
- As a user, I want one-click copy of the embed snippet and a demo page link so that I can test integration.

## 6. Requirements
### Functional
- Router: `/login`, `/register`, `/` (redirect by auth), `/dashboard`, `/agents/:id` (tabs: configure | knowledge | preview | embed). Auth guard.
- Store (Pinia): `auth` (token + user, persisted in localStorage, restore via `/me`), `agents`, `sources`, `chat`.
- API client: typed fetch wrapper with auth header injection and error normalization.
- Views:
  - `LoginView`, `RegisterView` — minimal forms, inline errors.
  - `DashboardView` — agent cards (avatar, name, source count, embed button) + "New Agent".
  - `AgentCreateView` — create + optional jump to detail.
  - `AgentDetailView` with tabs.
  - `ConfigureTab` — editable personalization form (live save).
  - `KnowledgeTab` — URL textarea (one per line), add; source list with status badges (pending/fetching/indexing/ready/failed) + error tooltip; re-index failed; delete; manual refresh via polling every 3s while any non-terminal status.
  - `PreviewTab` — SSE chat component (shared with widget logic): messages, streaming text, tool indicator, sources; thread persists per agent in sessionStorage.
  - `EmbedTab` — shows generated snippet in a read-only textarea, copy button, "Open demo page" link, token display + regenerate.
- Component tests (Vitest + @vue/test-utils + jsdom) for: auth store, api client, chat SSE parser, a form component.
### Non-Functional
- Minimal clean CSS (no heavy UI framework for MVP; hand-rolled utility styles).
- Consistent design tokens (colors from a small CSS file).
- Accessible basics: labels, focus states, keyboard submit.

## 7. Acceptance Criteria
- [ ] Unauthenticated users are redirected to /login; authed users redirected away from /login.
- [ ] Register + login flows work against the backend and persist token.
- [ ] Create agent → appears in dashboard list.
- [ ] Knowledge tab adds URLs, shows live status changes, and reaches `ready`.
- [ ] Preview tab streams a reply (integration with backend).
- [ ] Embed tab copies the snippet; demo page button opens /demo.html.
- [ ] `bun test:unit`, `bun run type-check`, `bun run build` all pass.

## 8. Out of Scope
- Dark mode, mobile app, design system library, SSR, i18n.
