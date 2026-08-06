# Feature PRD: Long Text as Knowledge Source

## 1. Feature Name
Pasted long-form text as a knowledge base source

## 2. Epic
- Epic PRD: `docs/ways-of-work/plan/agent-plug-mvp/epic.md`

## 3. Goal
**Problem:** Some knowledge lives only in a user's head or an internal document — not on a URL, and not in a PDF. Users need a way to paste that content directly.
**Solution:** A third source kind, `text`: users paste long-form text (with an optional title) which is chunked, embedded, and indexed exactly like URL/PDF sources — no fetch, no file needed.
**Impact:** Covers content that is not publicly hosted; unified pipeline (`kind=url | pdf | text`).

## 4. User Personas
- Maker / Developer
- Business Owner

## 5. User Stories
- As a user, I want to paste a long text as a knowledge source so that the agent can answer from it.
- As a user, I want to give it a title so that citations are readable.
- As a user, I want to remove it later so that the agent stops using it.

## 6. Requirements
### Functional
- `POST /api/agents/{id}/sources/text` — body `{title?, content}`; content min 10 chars, max 200k chars; title default "Pasted text".
- Creates `Source(kind='text', url='text://{uuid}', title, text_content)` with status `pending`.
- Pipeline branch: `kind='text'` → chunk/embed `text_content` directly (title from source). Startup rebuild re-indexes from stored text (no network/file).
- Delete works like other sources (nothing to clean from disk).
- `SourceResponse` exposes `kind`; content not returned in lists.
- Source marker parser + clients accept `text://` citations; rendered as a non-link label (like PDF).
### Non-Functional
- Idempotent migration (`text_content` column via `ALTER ... IF NOT EXISTS`).
- Stored in Postgres TEXT column; no file I/O.

## 7. Acceptance Criteria
- [ ] Creating a text source returns it with `kind=text` and status pending.
- [ ] Empty/short content → 422.
- [ ] Pipeline indexes `text_content` to chunks with `text://` metadata (unit test).
- [ ] Status reaches `ready` with chunk_count > 0.
- [ ] Citations show `📝 title` label (not a broken link).
- [ ] Frontend Knowledge tab has a "Text" input mode (title + content textarea).
- [ ] All backend + frontend tests pass.

## 8. Out of Scope
- File uploads beyond PDF (txt/md import), text editing after creation, character-level citations.
