---
description: Reproduce and fix a specific issue with the smallest safe code change.
argument-hint: "[issue description, test failure, or ticket]"
allowed-tools: Read, Grep, Glob, Bash, Edit, MultiEdit, Write
---

# /fix-issue

Fix this issue: `$ARGUMENTS`.

Workflow:

1. Reproduce or localize the problem with the smallest relevant command, test, or
   code inspection.
2. Identify the owning backend/frontend layer and the contract that failed.
3. Make the smallest maintainable change that fits existing patterns.
4. Add or update a focused test when the issue is behavioral or regression-prone.
5. Run targeted verification first, then broader checks if the touched surface is
   shared.
6. Report the root cause, files changed, and verification result.

Constraints:

- Do not rewrite unrelated code.
- Do not modify runtime APIs or database schema unless the issue requires it.
- If a model/schema change is required, create and review an Alembic migration.
- Preserve relative frontend API paths and `sessionStorage` auth behavior.
- Do not read or expose `.env`, `backend/.env`, `backend/app.db`, or secrets.
