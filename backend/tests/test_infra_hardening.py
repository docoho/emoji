from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock

import pytest
from alembic import command
from alembic.config import Config
from fastapi import HTTPException

from app.core import redis_client
from app.core.oauth_codes import RedisOAuthCodeStore, _OAuthCodeStore, create_oauth_code_store
from app.core.ratelimit import RateLimiter


class FakeRedis:
    def __init__(self) -> None:
        self.now = 0.0
        self.values: dict[str, tuple[object, Optional[float]]] = {}

    def advance(self, seconds: float) -> None:
        self.now += seconds

    def _purge(self, key: str) -> None:
        entry = self.values.get(key)
        if entry is None:
            return
        _, expiry = entry
        if expiry is not None and self.now >= expiry:
            del self.values[key]

    def ping(self) -> bool:
        return True

    def incr(self, key: str) -> int:
        self._purge(key)
        value, expiry = self.values.get(key, (0, None))
        count = int(value) + 1
        self.values[key] = (count, expiry)
        return count

    def expire(self, key: str, seconds: int) -> bool:
        self._purge(key)
        if key not in self.values:
            return False
        value, _ = self.values[key]
        self.values[key] = (value, self.now + seconds)
        return True

    def set(self, key: str, value: object, ex: Optional[int] = None, nx: bool = False) -> bool:
        self._purge(key)
        if nx and key in self.values:
            return False
        expiry = self.now + ex if ex is not None else None
        self.values[key] = (value, expiry)
        return True

    def get(self, key: str) -> object | None:
        self._purge(key)
        entry = self.values.get(key)
        return None if entry is None else entry[0]

    def getdel(self, key: str) -> object | None:
        value = self.get(key)
        if value is not None:
            del self.values[key]
        return value

    def delete(self, key: str) -> int:
        existed = key in self.values
        self.values.pop(key, None)
        return int(existed)


def _request(ip: str = "203.0.113.10") -> MagicMock:
    request = MagicMock()
    request.client = MagicMock()
    request.client.host = ip
    request.headers = {}
    return request


def test_unset_redis_url_uses_memory_stores() -> None:
    limiter = RateLimiter(max_requests=1, window_seconds=60, redis_url="")
    assert not limiter.uses_redis
    assert isinstance(create_oauth_code_store(redis_url=""), _OAuthCodeStore)


def test_configured_redis_url_selects_redis_stores() -> None:
    limiter = RateLimiter(max_requests=1, window_seconds=60, redis_url="redis://localhost:6379/0")
    assert limiter.uses_redis
    assert isinstance(
        create_oauth_code_store(redis_url="redis://localhost:6379/0"),
        RedisOAuthCodeStore,
    )


def test_configured_unavailable_redis_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailingRedis:
        def ping(self) -> None:
            raise ConnectionError("no redis here")

    monkeypatch.setattr(redis_client, "create_redis_client", lambda redis_url=None: FailingRedis())

    with pytest.raises(RuntimeError, match="Redis is unavailable"):
        redis_client.validate_redis_connection("redis://localhost:6379/0")


def test_redis_rate_limiter_allows_then_blocks() -> None:
    limiter = RateLimiter(
        max_requests=2,
        window_seconds=60,
        name="test",
        redis_url="redis://localhost:6379/0",
        redis_client=FakeRedis(),
    )

    limiter.check(_request())
    limiter.check(_request())

    with pytest.raises(HTTPException) as exc_info:
        limiter.check(_request())
    assert exc_info.value.status_code == 429


def test_redis_oauth_code_exchange_is_one_time() -> None:
    store = RedisOAuthCodeStore(
        ttl_seconds=30,
        redis_url="redis://localhost:6379/0",
        redis_client=FakeRedis(),
    )

    code = store.create("jwt-value")
    assert store.exchange(code) == "jwt-value"
    assert store.exchange(code) is None


def test_redis_oauth_code_expiry() -> None:
    fake = FakeRedis()
    store = RedisOAuthCodeStore(
        ttl_seconds=5,
        redis_url="redis://localhost:6379/0",
        redis_client=fake,
    )

    code = store.create("jwt-value")
    fake.advance(5)

    assert store.exchange(code) is None
    assert store.exchange("missing") is None


def test_alembic_upgrade_builds_current_sqlite_schema(tmp_path: Path) -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    db_path = tmp_path / "alembic.sqlite3"
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

    command.upgrade(config, "head")

    connection = sqlite3.connect(db_path)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        assert {
            "alembic_version",
            "collection",
            "collectionemoji",
            "emojicomment",
            "emojilike",
            "emojireport",
            "emojisubmission",
            "user",
        } <= tables

        emoji_columns = {
            row[1] for row in connection.execute("PRAGMA table_info('emojisubmission')")
        }
        assert {"moderation_status", "moderation_reason", "moderated_at"} <= emoji_columns

        collection_indexes = {
            row[1] for row in connection.execute("PRAGMA index_list('collection')")
        }
        assert "idx_collection_owner_kind" in collection_indexes

        like_indexes = {row[1] for row in connection.execute("PRAGMA index_list('emojilike')")}
        assert "idx_emojilike_emoji_created" in like_indexes
    finally:
        connection.close()


def test_alembic_schema_matches_sqlmodel_metadata(tmp_path: Path) -> None:
    """Every column on a SQLModel table must exist in the Alembic-head schema and
    vice versa. Catches drift between SQLModel.metadata.create_all (used by
    init_db for tests/dev seeds) and the Alembic revisions that own production.

    Compares column *names* only — types vary across backends and would make the
    assertion brittle. If this fails, a model gained/lost a column without a
    matching Alembic revision.
    """
    import app.models  # noqa: F401 - register tables on SQLModel.metadata
    from sqlalchemy import create_engine as sa_create_engine, inspect
    from sqlmodel import SQLModel

    backend_dir = Path(__file__).resolve().parents[1]
    db_path = tmp_path / "drift.sqlite3"
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(config, "head")

    engine = sa_create_engine(f"sqlite:///{db_path}")
    try:
        inspected_columns = {
            table.lower(): {col["name"] for col in inspect(engine).get_columns(table)}
            for table in inspect(engine).get_table_names()
        }
    finally:
        engine.dispose()

    # Only compare model-backed tables; ignore alembic_version and any helper tables.
    model_tables = {
        name.lower(): {col.name for col in table.columns}
        for name, table in SQLModel.metadata.tables.items()
    }

    assert set(model_tables) <= set(inspected_columns), (
        f"SQLModel declares tables absent from Alembic: "
        f"{sorted(set(model_tables) - set(inspected_columns))}"
    )

    for table_name, declared in sorted(model_tables.items()):
        actual = inspected_columns[table_name]
        missing_in_db = declared - actual
        extra_in_db = actual - declared
        assert not missing_in_db, (
            f"{table_name}: columns in model but missing from Alembic schema: "
            f"{sorted(missing_in_db)}"
        )
        assert not extra_in_db, (
            f"{table_name}: columns in Alembic schema but not on model: "
            f"{sorted(extra_in_db)}"
        )


def test_run_alembic_upgrade_stamps_legacy_db_then_upgrades(tmp_path: Path, monkeypatch) -> None:
    """A pre-Alembic prod DB (schema in place but no alembic_version) is stamped, then upgraded."""
    import app.db as db_module
    import app.models  # noqa: F401 - register tables on SQLModel.metadata
    from sqlalchemy import create_engine as sa_create_engine
    from sqlmodel import SQLModel

    db_path = tmp_path / "legacy.sqlite3"
    legacy_engine = sa_create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    SQLModel.metadata.create_all(legacy_engine)

    monkeypatch.setattr(db_module, "engine", legacy_engine)
    monkeypatch.setattr(db_module.settings, "database_url", f"sqlite:///{db_path}")

    db_module.run_alembic_upgrade()

    verify = sqlite3.connect(db_path)
    try:
        tables = {
            row[0]
            for row in verify.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        assert "alembic_version" in tables
        version = verify.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        assert version == "20260513_0001"
    finally:
        verify.close()


def test_run_alembic_upgrade_creates_schema_on_fresh_db(tmp_path: Path, monkeypatch) -> None:
    """A completely empty DB is built from scratch by Alembic (no stamp needed)."""
    import app.db as db_module
    from sqlalchemy import create_engine as sa_create_engine

    db_path = tmp_path / "fresh.sqlite3"
    fresh_engine = sa_create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    monkeypatch.setattr(db_module, "engine", fresh_engine)
    monkeypatch.setattr(db_module.settings, "database_url", f"sqlite:///{db_path}")

    db_module.run_alembic_upgrade()

    verify = sqlite3.connect(db_path)
    try:
        tables = {
            row[0]
            for row in verify.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        assert {"alembic_version", "user", "emojisubmission"} <= tables
        version = verify.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        assert version == "20260513_0001"
    finally:
        verify.close()


def test_enforce_required_secrets_fails_in_production(monkeypatch) -> None:
    """Production startup must abort if SECRET_KEY or OAUTH_STATE_SECRET is empty."""
    import logging
    from app.core.config import settings
    from app.main import _enforce_required_secrets

    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "secret_key", "")
    monkeypatch.setattr(settings, "oauth_state_secret", "non-empty-but-other-missing")

    logger = logging.getLogger("test_required_secrets")
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        _enforce_required_secrets(logger)


def test_enforce_required_secrets_passes_when_set(monkeypatch) -> None:
    """Production startup proceeds when both secrets are set."""
    import logging
    from app.core.config import settings
    from app.main import _enforce_required_secrets

    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "secret_key", "configured-jwt-secret")
    monkeypatch.setattr(settings, "oauth_state_secret", "configured-oauth-state-secret")

    logger = logging.getLogger("test_required_secrets")
    _enforce_required_secrets(logger)  # should not raise


def _patch_lifespan_for_tmp_db(tmp_path: Path, monkeypatch) -> None:
    """Point the app's engine + DB URL at a tmp file and neuter Redis validation
    so lifespan startup never touches backend/app.db or a real Redis."""
    import app.db as db_module
    from sqlalchemy import create_engine as sa_create_engine

    db_path = tmp_path / "lifespan.sqlite3"
    fake_engine = sa_create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    monkeypatch.setattr(db_module, "engine", fake_engine)
    monkeypatch.setattr(db_module.settings, "database_url", f"sqlite:///{db_path}")
    # validate_redis_connection is imported by name into app.main, so patch there.
    monkeypatch.setattr("app.main.validate_redis_connection", lambda *a, **kw: None)


def test_lifespan_aborts_in_production_with_missing_secrets(tmp_path: Path, monkeypatch) -> None:
    """Entering the app lifespan in production without required secrets must
    raise RuntimeError before serving any request."""
    from fastapi.testclient import TestClient

    from app.core.config import settings
    from app.main import app

    _patch_lifespan_for_tmp_db(tmp_path, monkeypatch)
    # Skip the Alembic round-trip so the test asserts the secret gate, not migrations.
    monkeypatch.setattr("app.main.run_alembic_upgrade", lambda *a, **kw: None)
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "secret_key", "")
    monkeypatch.setattr(settings, "oauth_state_secret", "")

    with pytest.raises(RuntimeError, match="Missing required secret"):
        with TestClient(app):
            pass


def test_lifespan_completes_when_secrets_present(tmp_path: Path, monkeypatch) -> None:
    """Entering the app lifespan in production with valid secrets serves requests."""
    from fastapi.testclient import TestClient

    from app.core.config import settings
    from app.main import app

    _patch_lifespan_for_tmp_db(tmp_path, monkeypatch)
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "secret_key", "configured-jwt-secret")
    monkeypatch.setattr(settings, "oauth_state_secret", "configured-oauth-state-secret")

    with TestClient(app) as client:
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


def test_settings_auto_generate_secrets_in_development() -> None:
    """A fresh dev-mode Settings instance gets non-empty secrets autoassigned."""
    from app.core.config import Settings

    s = Settings(environment="development", secret_key="", oauth_state_secret="")
    assert s.secret_key
    assert s.oauth_state_secret


def test_settings_does_not_auto_generate_in_production() -> None:
    """A production-mode Settings instance keeps empty secrets empty (so startup can detect)."""
    from app.core.config import Settings

    s = Settings(environment="production", secret_key="", oauth_state_secret="")
    assert s.secret_key == ""
    assert s.oauth_state_secret == ""
