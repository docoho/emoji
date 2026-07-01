---
description: Review the current changes for correctness, regressions, security, and missing tests.
argument-hint: "[optional scope, branch, PR, or files]"
allowed-tools: Read, Grep, Glob, Bash
---

# /review

Review the requested scope: `$ARGUMENTS`.

Follow this workflow:

1. Inspect repository status and the relevant diff before judging behavior.
2. Read the touched code and nearby tests/configuration that determine behavior.
3. Prioritize findings over summaries. Report real defects, regressions, security
   issues, data loss risks, broken migrations, and missing tests.
4. Use file and line references for every finding.
5. If no issues are found, say so clearly and name any residual risk or test gap.

Project-specific checks:

- Backend endpoints must use the correct auth dependency:
  `get_current_user` for required auth, `get_optional_user` for mixed anonymous
  and signed-in behavior.
- SQLModel changes require an Alembic revision and should satisfy the schema
  drift test.
- Frontend API calls must stay relative to `/api/...`.
- Auth tokens belong in `sessionStorage`; do not reintroduce `localStorage`.
- Shared composables intentionally keep module-level reactive state.
- Avoid weakening CORS, CSP, HSTS, rate limits, OAuth state validation, or JWT
  token-version checks.

Output format:

- Findings first, ordered by severity.
- Then open questions or assumptions.
- Then a brief change summary only if useful.
