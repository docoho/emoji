from __future__ import annotations

import secrets
import time
from threading import Lock
from typing import Any, Optional

from .config import settings
from .redis_client import create_redis_client


class _OAuthCodeStore:
    """Thread-safe in-memory store for one-time OAuth exchange codes."""

    def __init__(self, ttl_seconds: int = 30) -> None:
        self._ttl = ttl_seconds
        self._codes: dict[str, tuple[str, float]] = {}  # code -> (jwt, expiry)
        self._lock = Lock()

    def create(self, jwt_token: str) -> str:
        code = secrets.token_urlsafe(32)
        with self._lock:
            self._purge()
            self._codes[code] = (jwt_token, time.monotonic() + self._ttl)
        return code

    def exchange(self, code: str) -> Optional[str]:
        with self._lock:
            self._purge()
            entry = self._codes.pop(code, None)
        if entry is None:
            return None
        jwt_token, expiry = entry
        if time.monotonic() > expiry:
            return None
        return jwt_token

    def _purge(self) -> None:
        now = time.monotonic()
        expired = [k for k, (_, exp) in self._codes.items() if now > exp]
        for k in expired:
            del self._codes[k]


class RedisOAuthCodeStore:
    """Redis-backed one-time OAuth exchange code store."""

    def __init__(
        self,
        ttl_seconds: int = 30,
        redis_url: Optional[str] = None,
        redis_client: Any = None,
    ) -> None:
        self._ttl = ttl_seconds
        self._redis_url = settings.redis_url if redis_url is None else redis_url
        self._redis_client = redis_client

    def _client(self) -> Any:
        if self._redis_client is None:
            self._redis_client = create_redis_client(self._redis_url)
        return self._redis_client

    @staticmethod
    def _key(code: str) -> str:
        return f"emoji:oauth-code:{code}"

    def create(self, jwt_token: str) -> str:
        client = self._client()
        # 256 bits of entropy — collision probability is vanishingly small.
        # If it ever happens, surface as an error rather than silently retrying.
        code = secrets.token_urlsafe(32)
        if not client.set(self._key(code), jwt_token, ex=self._ttl, nx=True):
            raise RuntimeError(
                "OAuth exchange code collision (256-bit secrets.token_urlsafe)"
            )
        return code

    def exchange(self, code: str) -> Optional[str]:
        client = self._client()
        key = self._key(code)
        if hasattr(client, "getdel"):
            value = client.getdel(key)
        else:
            value = client.get(key)
            if value is not None:
                client.delete(key)
        if isinstance(value, bytes):
            return value.decode()
        return value


def create_oauth_code_store(redis_url: Optional[str] = None) -> _OAuthCodeStore | RedisOAuthCodeStore:
    url = settings.redis_url if redis_url is None else redis_url
    if url:
        return RedisOAuthCodeStore(redis_url=url)
    return _OAuthCodeStore()


oauth_code_store = create_oauth_code_store()

__all__ = ["RedisOAuthCodeStore", "_OAuthCodeStore", "create_oauth_code_store", "oauth_code_store"]
