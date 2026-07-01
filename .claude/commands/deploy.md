---
description: Prepare a deployment checklist and run safe pre-deploy verification. Manual invocation only.
argument-hint: "[environment or target]"
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash
---

# /deploy

Prepare deployment for: `$ARGUMENTS`.

This command is manual-only. Do not deploy, push, restart production services, or
change remote infrastructure unless the user explicitly asks for that exact
action after verification.

Pre-deploy workflow:

1. Confirm the target environment from `$ARGUMENTS`.
2. If the target is missing or ambiguous, stop and report what must be confirmed.
3. Inspect current git status and identify pending local changes.
4. Run backend checks:
   - `rtk make lint`
   - `rtk make backend-test`
   - `cd backend && rtk ./venv/bin/alembic upgrade head` when migrations changed.
5. Run frontend build:
   - `cd frontend && rtk npm run build`
6. Summarize readiness, blockers, and manual deployment steps.

Deployment safety:

- Never print secrets or read env files.
- Do not assume production credentials are available.
- Do not run destructive commands or remote mutations without explicit approval.
