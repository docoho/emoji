from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from sqlmodel import Session, SQLModel, create_engine

from .core.config import settings

ALEMBIC_BASELINE_REVISION = "20260429_0001"

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)


def init_db() -> None:
    """Register all models and create any missing tables for the active engine.

    Tests call this against in-memory engines. Production startup uses
    `run_alembic_upgrade()` instead — schema evolution is Alembic-managed.
    """
    import app.models  # noqa: F401 - ensure models are registered
    SQLModel.metadata.create_all(bind=engine)


def _alembic_config() -> Any:
    from alembic.config import Config
    backend_root = Path(__file__).resolve().parents[1]
    cfg = Config(str(backend_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    return cfg


def _stamp_legacy_if_needed(cfg: Any) -> None:
    """If the DB has app tables but no alembic_version, stamp the baseline.

    The deployed prod DB was built by the old hand-rolled `init_db` ALTER blocks,
    so `alembic_version` doesn't exist there. Stamping marks the schema as already
    at baseline so a subsequent `upgrade head` is a no-op (or applies only future
    revisions). New/empty DBs skip the stamp and let `upgrade` run normally.
    """
    from alembic import command
    from sqlalchemy import inspect

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "alembic_version" in table_names:
        return
    if "user" not in table_names or "emojisubmission" not in table_names:
        return
    command.stamp(cfg, ALEMBIC_BASELINE_REVISION)


def run_alembic_upgrade() -> None:
    """Run Alembic migrations to head, with a self-healing stamp for legacy DBs."""
    from alembic import command

    cfg = _alembic_config()
    _stamp_legacy_if_needed(cfg)
    command.upgrade(cfg, "head")


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


__all__ = ["engine", "get_session", "init_db", "run_alembic_upgrade"]
