# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Overview

Emoji Showcase Platform — a full-stack web app for sharing and curating emojis. Backend: FastAPI + SQLModel + SQLite. Frontend: Vue 3 + Vite. Deployed at emoji.undov.com.

## Commands

### Backend

```bash
cd backend
pip install -e ".[dev]"          # Install dependencies
uvicorn app.main:app --reload    # Run dev server (port 8000)
pytest                           # Run all tests
pytest tests/test_auth.py        # Run single test file
pytest -k "test_login"           # Run specific test by name
ruff check app tests             # Lint
```

Note: The venv is at `backend/venv/`. When running from the Makefile or outside the venv, use `./venv/bin/python -m pytest` and `./venv/bin/ruff`.

### Frontend

```bash
cd frontend
npm install
npm run dev    # Dev server (port 5173)
npm run build  # Production build
```

### Both (via Makefile)

```bash
make backend        # Run backend
make frontend       # Run frontend
make backend-test   # Run pytest
make lint           # Run ruff
make run-bg         # Run both in background
make stop           # Stop background services
```

If port 8000 is already in use after `make stop`, force-kill with `kill $(lsof -ti :8000)`.

### First-Time Setup

Run `./setup.sh` to auto-install Python 3.9+, Node.js 16+, create the venv, install all deps, and generate a `.env` template. Supports macOS (Homebrew) and Linux (apt, dnf, pacman).

## Architecture

### Request Flow

The frontend uses **relative paths** (`/api/...`) exclusively. Vite proxies `/api/*` to `http://127.0.0.1:8000` in dev, so the frontend never makes direct cross-origin requests. This is why `api.js` must not use absolute URLs.

### Backend Structure

```
backend/app/
├── main.py              # App factory (create_app) with CORS + security headers middleware
├── db.py                # DB engine, session provider, SQLite migration checks on startup
├── api/
│   ├── routes.py        # Aggregates all routers (auth, oauth, emojis, users)
│   ├── deps.py          # get_current_user, get_optional_user, get_current_active_superuser
│   └── endpoints/
│       ├── auth.py      # Register, login, /me, password reset
│       ├── emojis.py    # CRUD + like/unlike + favorites/popular sort
│       ├── oauth.py     # Google OAuth2 initiate + callback
│       └── users.py     # Public user profiles
├── core/
│   ├── config.py        # Settings (loads from .env via pydantic-settings)
│   ├── security.py      # bcrypt hashing, JWT encode/decode (PyJWT)
│   ├── oauth.py         # Google OAuth state generation/validation
│   ├── oauth_codes.py   # In-memory one-time auth code store (30s TTL)
│   ├── ratelimit.py     # In-memory per-IP rate limiter
│   └── email.py         # Email sending (password reset)
├── models/
│   ├── __init__.py      # Re-exports all models (import this to register them)
│   ├── emoji.py         # EmojiSubmission table
│   ├── user.py          # User table (includes OAuth + token_version fields)
│   └── like.py          # EmojiLike table (user_id + emoji_id unique constraint)
└── schemas/             # Pydantic request/response schemas
```

### Frontend Structure

```
frontend/src/
├── services/api.js           # All API calls (must use relative paths)
├── composables/
│   ├── useAuth.js            # Auth state (token in localStorage, user object)
│   ├── useTheme.js           # Dark/light theme toggle (system preference detection)
│   └── useToast.js           # Shared toast notification queue
├── components/
│   ├── EmojiCard.vue         # Card with copy, like, edit/delete, submitter link
│   ├── EmojiGrid.vue         # Responsive grid + detail modal
│   ├── EmojiSubmitForm.vue   # Emoji submission form
│   └── ToastContainer.vue    # Animated toast renderer (Teleported to body)
├── router/index.js           # Routes including OAuth callback + user profiles
└── views/                    # Page components
```

### Key Patterns

**Composables use module-level shared state.** `useAuth`, `useTheme`, and `useToast` all declare reactive state (`ref`/`reactive`) outside the exported function, so every component calling the composable shares the same instance. This is intentional — do not move state inside the function.

**Two auth dependencies.** `get_current_user` (401 if no token) and `get_optional_user` (returns None if no token). Use `get_optional_user` for endpoints that behave differently for authenticated vs anonymous users (e.g., `list_emojis` computes `is_liked` only when authenticated).

**Theming via CSS custom properties.** `style.css` defines ~30 CSS variables on `:root` for light theme and `[data-theme="dark"]` for dark theme. Vue scoped styles reference these variables. The `data-theme` attribute is set on `<html>` by `useTheme.js`.

**In-memory stores are single-worker only.** Both `RateLimiter` (ratelimit.py) and `_OAuthCodeStore` (oauth_codes.py) use in-memory dicts. They work because the app runs with a single uvicorn worker. Multi-worker deployment would require migrating these to Redis or similar.

**Token versioning invalidates JWTs.** `User.token_version` is embedded in JWTs as `ver`. When a password is reset, the version is incremented, invalidating all previously issued tokens. Both `get_current_user` and `get_optional_user` check this.

**Frontend mock data fallback.** `api.js:fetchEmojis()` falls back to local mock data when the backend is unreachable, enabling frontend-only development.

### Authentication

Two auth flows both issue JWT tokens stored in `localStorage`:

1. **Email/password**: `POST /api/auth/login` → JWT token
2. **Google OAuth2**: Frontend calls `POST /api/auth/oauth/google/login` → gets Google auth URL → redirect → backend callback at `GET /api/auth/oauth/google/callback` → backend redirects to frontend with auth code → `OAuthCallbackView.vue` exchanges code for JWT via `POST /api/auth/oauth/exchange`

State tokens (CSRF protection) are validated with 15-minute expiry. The OAuth callback endpoint is on the **backend** (`/api/auth/oauth/google/callback`), not the frontend route (`/auth/google/callback`).

### Database

SQLite at `backend/app.db` (auto-created). `db.py` runs schema migration checks on every startup (adds missing columns for OAuth fields). No migration framework — migrations are manual `ALTER TABLE` checks in `init_db()`. Add new migrations there when changing models. New tables (like `EmojiLike`) are created automatically by `SQLModel.metadata.create_all()` — just ensure the model is imported in `init_db()`.

### Likes System

- `EmojiLike` model with unique constraint on `(user_id, emoji_id)`
- `POST/DELETE /api/emojis/{id}/like` — idempotent like/unlike endpoints
- `list_emojis` computes `like_count` (GROUP BY query) and `is_liked` (user's liked set) as two separate queries, then merges into response
- Batch submitter name lookup avoids N+1 queries: collects all `submitter_id`s, fetches names in one query
- `sort=popular` orders by like count; `favorites=true` filters to user's liked emojis

### Emoji Permissions

- `GET /api/emojis` — public, supports `search`, `category`, `sort`, `limit`, `offset`, `favorites` query params
- `POST /api/emojis` — requires JWT
- `PUT/DELETE /api/emojis/{id}` — requires JWT and ownership (`submitter_id == current_user.id`)
- `POST/DELETE /api/emojis/{id}/like` — requires JWT

### Key Settings (`backend/app/core/config.py`)

All settings load from `.env` or environment variables:
- `SECRET_KEY` — JWT signing key (default is insecure dev value)
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — required for OAuth
- `GOOGLE_REDIRECT_URI` — must match Google Console config (points to `/api/auth/oauth/google/callback`)
- `FRONTEND_URL` — used for OAuth redirect back to frontend after login
- `OAUTH_STATE_SECRET` — signs CSRF state tokens

### Gotchas

- An HTTP proxy env var (`http_proxy`) can intercept localhost requests. Use `--noproxy localhost` with curl when testing locally.
- `make stop` may not kill all processes. Verify with `lsof -i :8000` if the port is still in use.
- In `App.vue`, the user RouterLink needs a `v-if="user"` guard because `isAuthenticated` (synchronous localStorage check) can be true while `user` (async API fetch) is still null.

### Testing

Tests use an in-memory SQLite database (via `StaticPool`) for isolation — no file-based DB is created. Key patterns in `conftest.py`:

- **`client` fixture** overrides FastAPI's `get_session` dependency to use the in-memory engine. Always use this fixture, not `TestClient(app)` directly.
- **Rate limiters auto-reset** via an `autouse` fixture, so rate limiting doesn't leak between tests.
- **Models must be imported** before `SQLModel.metadata.create_all()` runs. The conftest does `import app.models` to ensure all tables are registered.

To register a user and get a token in tests:
```python
client.post("/api/auth/register", json={"email": "...", "password": "...", "username": "..."})
resp = client.post("/api/auth/login", data={"username": "...", "password": "..."})
token = resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
```

### Linting

Ruff is configured in `pyproject.toml`: line-length 100, target Python 3.9. Run with `make lint` or `cd backend && ruff check app tests`.
