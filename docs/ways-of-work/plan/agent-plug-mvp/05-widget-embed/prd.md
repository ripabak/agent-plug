# Feature PRD: Embeddable Widget (HTML Injection)

## 1. Feature Name
Embeddable widget — floating chat bot via HTML injection

## 2. Epic
- Epic PRD: `docs/ways-of-work/plan/agent-plug-mvp/epic.md`

## 3. Goal
**Problem:** Customers must be able to add the agent to any external website with zero framework knowledge.
**Solution:** Backend serves a self-contained widget script (`GET /api/public/widget.js`). The embed snippet is a `<script>` tag with `data-agent-id` and `data-token` attributes (the identifier + auth). The widget renders a floating button at bottom-right; clicking opens a chat panel that loads agent config (name, welcome message, theme) and speaks to the public SSE endpoints.
**Impact:** Copy-paste embed; the core "plug into any website" promise of the product.

## 4. User Personas
- Maker / Developer
- Business Owner

## 5. User Stories
- As a user, I want to copy a small HTML snippet so that I can add the bot to my website.
- As a visitor, I want a floating button bottom-right and a clean chat panel so that I can start chatting immediately.
- As a visitor, I want to see the bot's name/avatar/theme matching the website brand.

## 6. Requirements
### Functional
- `GET /api/agents/{id}/embed` (auth) returns:
  ```html
  <script src="{BACKEND_URL}/api/public/widget.js" data-agent-id="{id}" data-token="{public_token}" data-base-url="{BACKEND_URL}"></script>
  ```
- `GET /api/public/widget.js` returns a plain JS module (no build step) that:
  - Reads `data-agent-id`, `data-token`, `data-base-url` from its own `<script>` tag.
  - Fetches `GET /api/public/agents/{id}/config` (token-authenticated) → `{name, description, welcome_message, theme_color, avatar_emoji}`.
  - Injects styles (scoped prefix `ap-widget-*`, z-index high, positioned bottom-right, respects mobile).
  - Renders floating button (avatar emoji on colored circle) + chat panel (header, messages, input, send).
  - Manages a thread id (sessionStorage, or `?ap_thread=` param) for continuity.
  - Sends messages: `POST /api/public/agents/{id}/commands` (run.start) then `POST /api/public/agents/{id}/stream` via `fetch` + `ReadableStream` SSE parsing.
  - Renders streaming text deltas, reasoning collapsed, tool indicator ("Searching knowledge base…"), and source links (urls from tool/retrieval citations).
  - Handles lifecycle completed/failed/cancelled; retry button on failure.
- Demo page served by frontend at `/demo.html` embedding the widget with a sample agent.
### Non-Functional
- No external dependencies in widget JS; must work on any modern browser.
- CSP-friendly: only injects its own styles; no remote fonts.
- Fails gracefully when backend is unreachable (shows retry).

## 7. Acceptance Criteria
- [ ] Embed snippet contains agent id + token + base URL.
- [ ] Widget JS is pure, dependency-free, and renders button + panel on a plain HTML page (tested via jsdom component test of extracted logic where feasible).
- [ ] Widget requests carry `X-Agent-Token` header (unit test of client logic).
- [ ] SSE parsing produces message objects from a mocked stream (unit test).
- [ ] Panel hides when clicking outside / close button (UI test with jsdom).
- [ ] Demo page loads and shows the floating button (manual + screenshot check).

## 8. Out of Scope
- React/Vue SDKs, dark/light theme auto-detection, i18n, custom fonts, proactivity (bot-initiated messages).
