# API Conventions

Use these rules for backend API changes and frontend API consumption.

## Backend API

- All application endpoints live under `/api`.
- Return consistent JSON error details through FastAPI `HTTPException`.
- Use query params consistently for list endpoints: `search`, `category`,
  `sort`, `limit`, `offset`, and feature-specific filters.
- Keep idempotent semantics for like/unlike and similar toggle endpoints where
  existing behavior is idempotent.
- Avoid N+1 queries by batching lookups for submitters, likes, collections,
  comments, and dashboard data.
- Validate ownership before mutation: emoji edits/deletes require matching
  `submitter_id`, admin routes require superuser checks.

## Frontend API

- Keep `API_BASE = ''` so Vite proxying and deployed same-origin routing work.
- Do not introduce direct `http://localhost`, `127.0.0.1`, or production absolute
  URLs in `frontend/src/services/api.js`.
- Propagate HTTP errors from the backend; use mock data fallback only for true
  dev-mode network failures.
- Dispatch and handle `auth:unauthorized` consistently on authenticated 401s.

## Schema and Migrations

- SQLModel model changes require an Alembic revision.
- Review autogeneration output before accepting it.
- Startup applies `alembic upgrade head`; do not add manual production
  `create_all()` migration paths.
