# AGENTS.md — frontend (agent-plug)

Vue 3 SPA (Vite + TypeScript) dashboard for Agent-Plug: auth, agent management,
knowledge base (URLs / PDFs / text), chat preview, embed snippet.
Read this file **before writing any frontend code**. For repo-wide context also
read the root `AGENTS.md`.

## Stack
- Node 22+ (bun 1.3+), Vue 3 `<script setup>` + TypeScript, Vite 8,
  vue-router 4, pinia 4
- Tests: Vitest 4 + @vue/test-utils + jsdom (existing setup)
- Lint/format: oxlint + eslint + prettier (existing setup)

## Layout
```
frontend/
  .env                      # VITE_API_BASE=http://localhost:8000
  src/
    main.ts                 # app bootstrap (pinia + router)
    App.vue                 # bare RouterView shell
    router/index.ts         # routes + auth guard (meta.auth / meta.guest)
    api/
      client.ts             # typed fetch wrapper (auth header, ApiError, upload)
      types.ts              # API types mirroring backend schemas (Source.kind: url|pdf|text)
    stores/
      auth.ts               # token + user (localStorage 'ap_token'), login/register/bootstrap
      agents.ts             # agent CRUD + sources for the detail page
      chat.ts               # chat display config: theme + Show thinking/tools (persisted to Agent)
    views/                  # Login, Register, Dashboard, AgentCreate, AgentDetail
    components/             # ConfigureTab, KnowledgeTab (3 input modes), PreviewTab, EmbedTab, StatusBadge
    assets/main.css         # minimal design system (no UI framework)
  public/demo.html          # widget demo page (query params: agent, token, base)
```

## Commands (run all before finishing)
```sh
bun install           # install deps (bun add <pkg>)
bun dev               # dev server (http://localhost:5173)
bun test:unit         # vitest unit tests — must pass
bun run type-check    # vue-tsc — must pass
bun lint              # oxlint + eslint — must pass
bun run build         # type-check + vite build — must pass
bun format            # prettier
```

## Conventions & Rules
- **Backend base URL**: `VITE_API_BASE` in `.env` (default
  `http://localhost:8000`), read in `src/api/client.ts` as `API_BASE`.
- **Auth**: token in `localStorage['ap_token']`; every request goes through the
  api client which injects `Authorization: Bearer …`. 401 → logout + redirect.
- **API types mirror backend**: update `src/api/types.ts` together with backend
  schemas (e.g. `Source.kind: 'url' | 'pdf' | 'text'`).
- **SSE chat contract**: methods `lifecycle`, `message_start`, `text_delta`
  (kind `text`|`reasoning`), `message_end`, `sources`, `tool_start`,
  `tool_end`, `tool_progress`. Reasoning + tool events are always emitted by
  the backend; the widget parses them client-side. The ⚙ toggles
  (`chat.settings`, persisted to the Agent) only hide/show them client-side.
- **Preview reuses the REAL widget — no parallel chat UI**: `PreviewTab.vue`
  embeds the actual `backend/app/widget/widget.js` (floating launcher + panel,
  `data-auto-open="desktop"` → auto-opens on desktop, launcher-only on
  mobile) instead of mirroring the chat in Vue. The chat UI exists ONCE, in
  `widget.js` — do NOT build a second chat rendering path. PreviewTab
  communicates with the widget through the `window.__apwWidgets[agentId]`
  bridge exposed by `widget.js` (`setTheme(theme)`, `setOpts(showThinking,
  showTools)`, `destroy()`); the initial theme is passed as a `data-theme`
  JSON attribute. Theme tokens live in `src/utils/themes.ts` and the theme
  object inside `widget.js` — keep them in sync (plus `--chat-*` defaults in
  `assets/main.css` for the config panel/`ColorPreview` mockups).
- **⚠️ PREVIEW == LIVE — config flows to the widget**: the chat display config
  (theme colors + Show thinking/Show tools toggles) is set **only** from the
  preview config panel (`PreviewTab.vue`) and is stored on the **Agent** via
  `PATCH /api/agents/{id}` (`chat_theme`, `show_thinking`, `show_tools`). The
  live widget is **not** configured independently: it reads the same values
  from `GET /api/public/agents/{id}/config` (plus optional `data-*` script
  overrides) and renders identically. So: **if the preview is changed, the
  live widget follows automatically** — never add per-widget controls, never
  store display config only in localStorage. The chat itself (preview header
  AND widget header) has **no ⚙ settings menu** — the preview panel is the
  single place to adjust. Shared tokens live in `src/utils/themes.ts`
  (preview) and the theme object inside `widget.js` (widget) and must stay in
  sync with the `--chat-*` defaults in `assets/main.css`.
- **Knowledge tab**: 3 input modes (🌐 URLs / 📄 PDF / 📝 Text) via the
  `source-modes` switcher; status polling every 3s while any source is
  pending/fetching/indexing.
- **Testing**: every new store/util/component gets a test under
  `src/**/__tests__/`. Mock `@/api/client` in store/component tests. IMPORTANT:
  the lint rule `vitest/require-mock-type-parameters` requires **typed** mocks —
  use `vi.fn<(args) => Promise<T>>()` for api mocks and `vi.fn<typeof fetch>()`
  for fetch (see `src/stores/__tests__/auth.spec.ts`, `chat.spec.ts`).
- **Design system**: keep all tokens/classes in `assets/main.css`; no
  component-scoped one-off colors. Preview chat styles there mirror the widget.
