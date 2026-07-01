# Testing Rules

Use focused tests for narrow changes and broader verification for shared
contracts.

## Backend

- Run backend tests with `cd backend && rtk ./venv/bin/python -m pytest`.
- Use the shared `client` fixture from `backend/tests/conftest.py`.
- Do not instantiate `TestClient(app)` directly in tests.
- Ensure `app.models` is imported before SQLModel metadata creation.
- Rely on the autouse rate limiter reset fixture; do not make tests order
  dependent.
- For auth setup, register through `/api/auth/register`, login through
  `/api/auth/login`, and pass `Authorization: Bearer <token>`.
- If models or migrations change, run the Alembic drift coverage in
  `tests/test_infra_hardening.py`.

## Frontend

- Run production build verification with `cd frontend && rtk npm run build`.
- When changing API behavior, verify frontend call sites still use relative
  paths and preserve error propagation.
- When changing auth UI/state, verify token expiry and 401 handling still clear
  `sessionStorage`.

## Documentation and Claude Config

- For Claude-only documentation/config changes, verify file presence, JSON
  validity, and git ignore behavior. Full app tests are not required unless app
  code changed.
