# Feature PRD: Agent Management & Personalization

## 1. Feature Name
Agent management & personalization

## 2. Epic
- Epic PRD: `docs/ways-of-work/plan/agent-plug-mvp/epic.md`

## 3. Goal
**Problem:** Users need a place to create and configure the AI agents they will embed.
**Solution:** CRUD endpoints + UI for agents with personalization fields (name, description, system prompt, welcome message, theme, avatar emoji). Every agent gets a unique `public_token` used later for widget auth.
**Impact:** Users can create multiple agents and differentiate their tone, greeting, and look before embedding.

## 4. User Personas
- Maker / Developer
- Business Owner

## 5. User Stories
- As a user, I want to create an agent so that I can later attach knowledge and embed it.
- As a user, I want to edit the system prompt and welcome message so that the bot matches my brand voice.
- As a user, I want to list/delete my agents so that I keep only what I need.
- As a user, I want to see the generated public token so that I understand what authenticates my embed.

## 6. Requirements
### Functional
- `POST /api/agents` — create (name required; description, system_prompt, welcome_message, theme_color, avatar_emoji optional). Generates `public_token` (secrets.token_urlsafe).
- `GET /api/agents` — list current user's agents (newest first).
- `GET /api/agents/{id}` — detail (must belong to user, else 404).
- `PATCH /api/agents/{id}` — update personalization fields.
- `DELETE /api/agents/{id}` — delete agent + its sources.
- `POST /api/agents/{id}/regenerate-token` — rotate public token.
- `GET /api/agents/{id}/embed` — return generated embed HTML snippet.
### Non-Functional
- All routes require auth; agents are user-scoped (multi-tenant via user_id).
- Tokens must be URL-safe, ≥ 32 chars.

## 7. Acceptance Criteria
- [ ] Create agent returns agent with generated public_token.
- [ ] List only returns current user's agents.
- [ ] Accessing/updating/deleting another user's agent returns 404.
- [ ] PATCH updates only provided fields.
- [ ] Regenerate-token changes the token and invalidates the old one (verification test).
- [ ] Embed endpoint returns HTML containing agent id + token.

## 8. Out of Scope
- Model selection, temperature UI, tool toggles per agent (MVP: fixed model + fixed RAG tool).
