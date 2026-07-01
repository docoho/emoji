---
name: security-review
description: Review this project for auth, OAuth, JWT, permission, secret, rate limit, Redis, CORS/CSP, and migration security risks.
when_to_use: Use for security audits, auth changes, OAuth changes, settings/config changes, permission-sensitive endpoints, deployment hardening, and review of code that touches secrets or database migrations.
allowed-tools: Read, Grep, Glob, Bash
---

# Security Review Skill

Review the requested scope for concrete security and reliability risks. Focus on
observable code paths and configuration, not generic advice.

Checklist:

1. Auth and authorization
   - Required endpoints use `get_current_user`.
   - Mixed public/private endpoints use `get_optional_user` safely.
   - Ownership checks protect emoji, collection, moderation, and creator actions.
   - Superuser-only endpoints require the active superuser dependency.
2. JWT and sessions
   - JWT creation/decoding validates expiry and token version.
   - Password reset increments `token_version`.
   - Frontend tokens remain in `sessionStorage`.
   - 401 handling clears session state.
3. OAuth
   - State tokens are generated, signed, expiry-checked, and single-purpose.
   - Callback and exchange flows do not leak tokens in logs or errors.
   - Redirect URIs come from configuration and match backend callback routes.
4. Secrets and local data
   - Do not read or print `.env`, `backend/.env`, `backend/app.db`, keys, or
     credentials.
   - Ensure new config examples contain placeholders only.
5. Request hardening
   - CORS remains constrained by settings.
   - CSP/HSTS/security headers are not weakened without justification.
   - Rate limits protect auth and abuse-prone routes.
   - Redis fallback/validation behavior is understood for production.
6. Database and migrations
   - SQLModel changes have Alembic revisions.
   - Migrations avoid destructive changes without explicit data handling.
   - Tests cover security-sensitive schema or permission behavior.

Output:

- Findings first, ordered by severity.
- Include exact file and line references.
- State exploit or failure scenario for each finding.
- If no finding is present, state residual risk and tests reviewed.
