# Code Style Rules

Use these rules when editing application code.

## Python Backend

- Target Python 3.9 and Ruff line length 100.
- Prefer existing FastAPI, SQLModel, Pydantic, and helper patterns.
- Keep endpoint logic small; move repeated response shaping or query helpers into
  existing helper modules when duplication becomes meaningful.
- Use explicit auth dependencies: required auth uses `get_current_user`, mixed
  public/private behavior uses `get_optional_user`.
- Avoid ad hoc SQL string construction; use SQLModel/SQLAlchemy expressions.
- Do not add schema changes without an Alembic revision.

## Vue Frontend

- Keep all API requests in `frontend/src/services/api.js` or a local service that
  delegates to it.
- API URLs must be relative `/api/...` paths.
- Keep auth token storage in `sessionStorage`.
- Preserve module-level shared state in composables such as `useAuth`,
  `useTheme`, `useToast`, and `useCollections`.
- Use CSS custom properties from `frontend/src/style.css` for colors, spacing,
  surfaces, and theme-aware styling.
- Build reusable components around existing component conventions before adding
  new abstractions.

## General

- Keep edits scoped to the requested behavior.
- Prefer small, readable functions over clever indirection.
- Do not commit generated caches, local databases, logs, env files, or private
  Claude local settings.
