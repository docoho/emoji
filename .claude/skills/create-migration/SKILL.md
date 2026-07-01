---
name: create-migration
description: Generate an Alembic revision for a SQLModel model change, review the autogenerate output, apply it, and verify there is no schema drift against the models.
when_to_use: Invoke after editing a file under backend/app/models/ (add/rename/drop a column, table, index, or constraint), or when asked to create, add, or generate a database migration.
allowed-tools: Read, Grep, Glob, Bash
---

# Create Migration Skill

Every SQLModel model change must ship with a matching Alembic revision. Production
schema is owned by Alembic only — never use `SQLModel.metadata.create_all()` as a
migration path. This skill turns a model edit into a reviewed, drift-free revision.

## Workflow

1. **Confirm the model change is saved.** The edited file under
   `backend/app/models/` must already be written; `app.models` is imported by
   `alembic/env.py`, so autogenerate reads from `SQLModel.metadata`.

2. **Find the current head.**
   ```
   cd backend && ./venv/bin/alembic heads
   ```

3. **Compute the revision id** using the project convention `YYYYMMDD_NNNN`
   (e.g. `20260623_0001`). Use today's date; if `backend/alembic/versions/`
   already contains a revision dated today, increment the `NNNN` sequence.

4. **Autogenerate the revision**, passing the id explicitly so it matches the
   convention instead of Alembic's default hex hash:
   ```
   cd backend && ./venv/bin/alembic revision --autogenerate --rev-id <YYYYMMDD_NNNN> -m "<snake_case_summary>"
   ```
   Alembic sets `down_revision` to the current head automatically and names the
   file `<id>_<summary>.py`.

5. **Review the generated file before accepting it.** Autogenerate is a draft,
   not a guarantee — read the whole file:
   - **Empty `upgrade()`/`downgrade()`** means Alembic saw no diff. Either the
     model wasn't imported, or the change isn't autodetectable (e.g. a changed
     `server_default`). Stop and write the op by hand.
   - Column types, `nullable`, and `server_default` match the model's intent.
   - **SQLite column drops/renames/type changes must use `op.batch_alter_table`**
     — SQLite cannot `ALTER COLUMN` directly. See
     `20260513_0001_drop_collectionemoji_position.py` for the pattern, including
     the introspect-before-alter guard for legacy DBs.
   - Destructive changes (drop column/table) state the data-handling or explicitly
     note data loss; the `security-review` skill flags silent destructive ops.
   - Docstring summarizes the change; `down_revision` chains to the prior head.

6. **Apply the migration.**
   ```
   cd backend && ./venv/bin/alembic upgrade head
   ```

7. **Verify there is no drift.** Run the Alembic coverage in
   `tests/test_infra_hardening.py`:
   ```
   cd backend && ./venv/bin/python -m pytest tests/test_infra_hardening.py -k "alembic or schema_matches or upgrade_builds"
   ```
   The key assertion is `test_alembic_schema_matches_sqlmodel_metadata`, which
   fails if any model column has no matching migration (or vice versa).

8. **Report** the new revision id, the table/columns affected, and the test
   result. Note any hand-written ops and why autogenerate was insufficient.

## Safety rules

- Never read or print `.env`, `backend/.env`, `backend/app.db`, private keys, or
  credential files.
- Never accept autogenerate output without reading it.
- Never use `create_all()` as a substitute for a revision in production paths.
- A revision is itself a change to migration config — surface destructive ops
  before committing.

## Related

- `.claude/rules/api-conventions.md` — schema and migration rules.
- `.claude/agents/security-auditor.md` and the `security-review` skill for
  auditing migrations that touch auth/permission-sensitive tables.
