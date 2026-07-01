# 🎨 Emoji Showcase Platform

A full-stack web application for sharing and curating emojis. Users can browse the gallery, submit their own entries, like favourites, and manage their contributions through an authenticated platform.

🌐 **Live**: [emoji.undov.com](https://emoji.undov.com)

---

## Features

| | |
|---|---|
| 🔐 **Authentication** | Email/password registration and login with JWT tokens |
| 🔑 **Google OAuth2** | Sign in with Google (CSRF-protected state tokens) |
| 📝 **Emoji Submissions** | Submit emojis with title, description, category, and keywords |
| ❤️ **Likes & Favorites** | Like emojis and filter the gallery to your favourites |
| 🔍 **Search & Filter** | Filter by category, search by keyword, sort by date or popularity |
| 👤 **Public Profiles** | Browse a creator's public page and their submissions |
| 🔁 **Password Reset** | Token-based reset flow via email (MailerSend) |
| 🛡️ **Rate Limiting** | Per-IP rate limiting on security-sensitive endpoints |

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | FastAPI (Python 3.9+) |
| **ORM / DB** | SQLModel + SQLite (auto-created at `backend/app.db`) |
| **Auth** | PyJWT + bcrypt (email/password) · Authlib + itsdangerous (OAuth2) |
| **Frontend** | Vue 3 (Composition API) + Vite |
| **Routing** | Vue Router 4 |
| **Testing** | pytest (in-memory SQLite) |
| **Linting** | Ruff |

---

## Project Structure

```
emoji/
├── Makefile                    # Dev commands (backend, frontend, test, lint)
├── setup.sh                    # Automated dependency setup
├── backend/
│   ├── pyproject.toml          # Python deps & tool config
│   ├── .env                    # Secret config (gitignored)
│   ├── .env.example            # Config template
│   ├── app/
│   │   ├── main.py             # FastAPI app factory (CORS + security headers)
│   │   ├── db.py               # DB engine, session, startup migrations
│   │   ├── core/
│   │   │   ├── config.py       # Settings (pydantic-settings / .env)
│   │   │   ├── security.py     # bcrypt hashing, JWT encode/decode
│   │   │   ├── oauth.py        # Google OAuth2 state generation/validation
│   │   │   ├── oauth_codes.py  # In-memory one-time auth code store (30 s TTL)
│   │   │   ├── ratelimit.py    # In-memory per-IP rate limiter
│   │   │   └── email.py        # Password-reset email (MailerSend)
│   │   ├── models/
│   │   │   ├── user.py         # User table (OAuth fields + token_version)
│   │   │   ├── emoji.py        # EmojiSubmission table
│   │   │   └── like.py         # EmojiLike table (unique: user_id + emoji_id)
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   └── api/
│   │       ├── routes.py       # Aggregates all routers
│   │       ├── deps.py         # get_current_user / get_optional_user
│   │       └── endpoints/
│   │           ├── auth.py     # Register, login, /me, password reset
│   │           ├── oauth.py    # Google OAuth initiate + callback
│   │           ├── emojis.py   # Emoji CRUD + like/unlike
│   │           └── users.py    # Public user profiles
│   └── tests/
│       ├── conftest.py         # Fixtures (in-memory DB, test client, auth helpers)
│       ├── test_auth.py
│       ├── test_emojis.py
│       ├── test_health.py
│       └── test_security.py
└── frontend/
    ├── vite.config.js          # Vite config (proxies /api → :8000)
    └── src/
        ├── services/api.js     # All API calls (relative paths only)
        ├── composables/
        │   ├── useAuth.js      # Shared reactive auth state (module-level)
        │   ├── useTheme.js     # Dark/light theme (system preference)
        │   └── useToast.js     # Shared toast notification queue
        ├── components/
        │   ├── EmojiCard.vue       # Card: copy, like, edit/delete, submitter link
        │   ├── EmojiGrid.vue       # Responsive grid + detail modal
        │   ├── EmojiSubmitForm.vue # Submission form
        │   └── ToastContainer.vue  # Animated toasts (Teleported to body)
        ├── router/index.js
        └── views/
            ├── HomeView.vue
            ├── LoginView.vue
            ├── RegisterView.vue
            ├── ForgotPasswordView.vue
            ├── ResetPasswordView.vue
            ├── OAuthCallbackView.vue
            └── UserProfileView.vue
```

---

## Architecture

### Request Flow

```
Browser ──▶ Vite dev proxy (/api/*) ──▶ FastAPI :8000 ──▶ SQLite (app.db)
```

The frontend uses **relative paths only** (`/api/...`). Vite proxies these to the backend in development, so no cross-origin requests are ever made.

### Authentication

Two flows, both issuing JWT tokens stored in `localStorage`:

1. **Email/password** — `POST /api/auth/login` → JWT
2. **Google OAuth2** — Frontend → Google → backend callback → short-lived code → `POST /api/auth/oauth/exchange` → JWT

**Token versioning**: `User.token_version` is embedded in every JWT as `ver`. Resetting a password increments this field, instantly invalidating all previously issued tokens.

### Key Design Decisions

- **No migration framework** — `db.py:init_db()` runs `ALTER TABLE` checks on every startup to add missing columns. New tables are auto-created by `SQLModel.metadata.create_all()`.
- **Likes system** — `EmojiLike` with a unique constraint on `(user_id, emoji_id)`. Like count via `GROUP BY`; submitter names fetched in a single batch query (no N+1).
- **In-memory stores** — Rate limiter and OAuth code store use in-memory dicts. Works because the app runs with a single uvicorn worker.
- **Frontend mock fallback** — `api.js:fetchEmojis()` falls back to local mock data when the backend is unreachable, enabling UI-only development.
- **Security headers** — CSP, X-Frame-Options, and Referrer-Policy are injected via middleware on every response.

---

## Getting Started

### Quick Setup (Recommended)

```bash
chmod +x setup.sh
./setup.sh
```

The script:
- Detects macOS / Linux (Debian, Fedora, Arch) and installs missing dependencies via the system package manager
- Requires Python ≥ 3.9 and Node.js ≥ 16 (installs via Homebrew / apt / dnf / pacman if absent)
- Creates `backend/venv` and runs `pip install -e ".[dev]"`
- Runs `npm install` in `frontend/`
- Removes stale packages from previous dependency swaps (e.g. `python-jose` → `PyJWT`)
- Copies `backend/.env.example` → `backend/.env` if no `.env` exists yet

**Partial setup flags:**

```bash
./setup.sh --backend-only   # Python venv + pip only
./setup.sh --frontend-only  # npm install only
./setup.sh --help
```

### Manual Setup

**Prerequisites**: Python 3.9+, Node.js 16+

```bash
# Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env      # then edit .env with your secrets

# Frontend
cd frontend
npm install
```

### Running the Servers

```bash
make run-bg      # start both servers in background
make stop        # stop background servers
```

Or individually:

```bash
make backend     # FastAPI at http://localhost:8000
make frontend    # Vite UI  at http://localhost:5173
```

Logs are written to `backend.log` and `frontend.log`.

---

## API Reference

### Authentication

| Method | Path | Auth | Description |
|--------|------|:----:|-------------|
| `POST` | `/api/auth/register` | — | Register a new user |
| `POST` | `/api/auth/login` | — | Login, receive JWT |
| `GET`  | `/api/auth/me` | ✓ | Current user profile |
| `POST` | `/api/auth/password-reset/request` | — | Request reset email |
| `POST` | `/api/auth/password-reset/confirm` | — | Confirm reset with token |

### Google OAuth2

| Method | Path | Auth | Description |
|--------|------|:----:|-------------|
| `POST` | `/api/auth/oauth/google/login` | — | Initiate Google OAuth flow |
| `GET`  | `/api/auth/oauth/google/callback` | — | Backend OAuth callback |
| `POST` | `/api/auth/oauth/exchange` | — | Exchange auth code for JWT |

### Emojis

| Method | Path | Auth | Description |
|--------|------|:----:|-------------|
| `GET`    | `/api/emojis` | — | List emojis (`search`, `category`, `sort`, `limit`, `offset`, `favorites`) |
| `POST`   | `/api/emojis` | ✓ | Submit a new emoji |
| `PUT`    | `/api/emojis/{id}` | ✓ | Update emoji (owner only) |
| `DELETE` | `/api/emojis/{id}` | ✓ | Delete emoji (owner only) |
| `POST`   | `/api/emojis/{id}/like` | ✓ | Like an emoji |
| `DELETE` | `/api/emojis/{id}/like` | ✓ | Unlike an emoji |

### Users & System

| Method | Path | Auth | Description |
|--------|------|:----:|-------------|
| `GET` | `/api/users/{username}` | — | Public user profile |
| `GET` | `/api/health` | — | Health check |

---

## Configuration

All settings are loaded from `backend/.env` (or environment variables):

```env
# Required
SECRET_KEY=change-me-to-a-random-secret
OAUTH_STATE_SECRET=change-me-to-another-random-secret

# Google OAuth2 (optional — required for Google sign-in)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/oauth/google/callback
FRONTEND_URL=http://localhost:5173

# MailerSend (optional — required for password-reset emails)
MAILERSEND_API_KEY=
MAIL_FROM=
```

Generate secure secrets with:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Testing

```bash
make backend-test
# or: cd backend && ./venv/bin/python -m pytest -v
```

Tests run against an **in-memory SQLite database** for full isolation. The `conftest.py` fixture overrides the FastAPI session dependency, auto-resets rate limiters between tests, and imports all models before table creation.

---

## Roadmap

Upcoming features are tracked in [FEATURE_ROADMAP.md](./FEATURE_ROADMAP.md).

---

## License

Licensed under the Apache License 2.0 — see [LICENSE](LICENSE) for details.
