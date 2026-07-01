---
name: deploy
description: Prepare this app for deployment by running safe verification and producing a readiness checklist.
when_to_use: Invoke manually before deployment, release preparation, production rollout checks, or when asked to verify deploy readiness.
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash
---

# Deploy Skill

This skill is manual-only. Do not deploy, push, restart services, mutate remote
infrastructure, or run destructive commands unless the user explicitly asks for
that exact action after readiness checks.

Deployment readiness workflow:

1. Confirm target environment and expected deployment mechanism.
2. Inspect git status and identify uncommitted changes.
3. Check whether backend models or migrations changed.
4. Run safe local verification:
   - `rtk make lint`
   - `rtk make backend-test`
   - `cd frontend && rtk npm run build`
   - `cd backend && rtk ./venv/bin/alembic upgrade head` if migrations changed.
5. Review configuration requirements:
   - `SECRET_KEY`
   - `OAUTH_STATE_SECRET`
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `GOOGLE_REDIRECT_URI`
   - `FRONTEND_URL`
   - Redis settings when production depends on Redis.
6. Report readiness, blockers, and manual next steps.

Safety rules:

- Never read or print `.env`, `backend/.env`, `backend/app.db`, private keys, or
  credential files.
- Do not assume production secrets or remote access.
- Stop if the deployment target is ambiguous.
