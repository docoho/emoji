from __future__ import annotations

from typing import Any, Optional

from .config import settings


def create_redis_client(redis_url: Optional[str] = None) -> Any:
    url = settings.redis_url if redis_url is None else redis_url
    if not url:
        return None
    try:
        from redis import Redis
    except ImportError as exc:  # pragma: no cover - exercised when dependency is missing
        raise RuntimeError("REDIS_URL is configured, but the redis package is not installed") from exc
    return Redis.from_url(url, decode_responses=True)


def validate_redis_connection(redis_url: Optional[str] = None) -> None:
    client = create_redis_client(redis_url)
    if client is None:
        return
    try:
        client.ping()
    except Exception as exc:
        raise RuntimeError("REDIS_URL is configured, but Redis is unavailable") from exc


__all__ = ["create_redis_client", "validate_redis_connection"]
