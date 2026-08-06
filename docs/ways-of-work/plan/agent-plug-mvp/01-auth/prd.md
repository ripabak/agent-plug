# Feature PRD: Authentication

## 1. Feature Name
Authentication (register, login, current user)

## 2. Epic
- Epic PRD: `docs/ways-of-work/plan/agent-plug-mvp/epic.md`

## 3. Goal
**Problem:** The dashboard (agent management, knowledge base, embed snippets) is per-user data. Without auth, any visitor could read or modify other users' agents.
**Solution:** Email+password auth with JWT bearer tokens; bcrypt password hashing.
**Impact:** Secures all user-scoped APIs; enables the dashboard to start immediately after signup.

## 4. User Personas
- Maker / Developer (dashboard user)
- Business Owner (dashboard user)

## 5. User Stories
- As a new user, I want to register with email + password so that I get an account and token immediately.
- As a returning user, I want to log in so that I can manage my agents.
- As an authenticated user, I want a `/me` endpoint so that my client can restore session on page reload.

## 6. Requirements
### Functional
- `POST /api/auth/register` — email, display_name, password → creates user (unique email), returns `{access_token, user}`.
- `POST /api/auth/login` — email + password → verifies, returns `{access_token, user}`.
- `GET /api/auth/me` — returns current user from Bearer token.
- Duplicate email → 400. Wrong credentials → 401.
- Token expiry configurable (default 7 days).
### Non-Functional
- Passwords hashed with bcrypt, never stored or logged in plaintext.
- JWT signed with server secret.

## 7. Acceptance Criteria
- [ ] Register with new email returns 200 + valid token; duplicate email returns 400.
- [ ] Login with correct credentials returns 200 + valid token; wrong password returns 401.
- [ ] `/me` with valid token returns the user; without/with invalid token returns 401.
- [ ] Passwords are bcrypt-hashed in DB (verified via unit test).
- [ ] Unit tests cover hashing, token create/decode, and the three endpoints.

## 8. Out of Scope
- OAuth / social login, email verification, password reset, refresh tokens.
