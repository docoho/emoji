from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any, Optional

from fastapi import HTTPException, Request, status

from .config import settings
from .redis_client import create_redis_client

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter keyed by client IP, backed by memory or Redis."""

    def __init__(
        self,
        max_requests: int,
        window_seconds: int,
        max_entries: int = 10_000,
        cleanup_interval: int = 100,
        name: str = "default",
        redis_url: Optional[str] = None,
        redis_client: Any = None,
    ) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.max_entries = max_entries
        self.cleanup_interval = cleanup_interval
        self.name = name
        self._redis_url = settings.redis_url if redis_url is None else redis_url
        self._redis_client = redis_client
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._check_count: int = 0

    @property
    def uses_redis(self) -> bool:
        return bool(self._redis_url or self._redis_client is not None)

    def _get_redis_client(self) -> Any:
        if self._redis_client is None:
            self._redis_client = create_redis_client(self._redis_url)
        return self._redis_client

    def _client_ip(self, request: Request) -> str:
        direct_ip = request.client.host if request.client else "unknown"
        # Only trust X-Forwarded-For if the direct client is a configured proxy.
        # The proxy list is read at call time so deployment changes (e.g.
        # adding a new ALB IP) take effect without restarting the limiter.
        if direct_ip in set(settings.trusted_proxy_ips):
            forwarded = request.headers.get("x-forwarded-for")
            if forwarded:
                return forwarded.split(",")[0].strip()
        return direct_ip

    def _cleanup_stale(self) -> None:
        """Remove IPs with no recent hits within the current window."""
        now = time.monotonic()
        cutoff = now - self.window_seconds
        stale_ips = [
            ip for ip, hits in self._hits.items()
            if not hits or max(hits) < cutoff
        ]
        for ip in stale_ips:
            del self._hits[ip]

    def _evict_if_full(self) -> None:
        """Drop the oldest IP entry when max_entries is exceeded."""
        if len(self._hits) <= self.max_entries:
            return
        oldest_ip = min(
            self._hits,
            key=lambda ip: min(self._hits[ip]) if self._hits[ip] else float("inf"),
        )
        del self._hits[oldest_ip]

    def _check_redis(self, ip: str) -> None:
        client = self._get_redis_client()
        if client is None:
            return
        bucket = int(time.time() // self.window_seconds)
        key = f"emoji:rate:{self.name}:{ip}:{bucket}"
        count = int(client.incr(key))
        if count == 1:
            client.expire(key, self.window_seconds * 2)
        if count > self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            )

    def check(self, request: Request) -> None:
        ip = self._client_ip(request)
        if self.uses_redis:
            self._check_redis(ip)
            return

        now = time.monotonic()
        cutoff = now - self.window_seconds

        # Prune expired entries for this IP
        hits = self._hits[ip]
        self._hits[ip] = [t for t in hits if t > cutoff]

        if len(self._hits[ip]) >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            )

        self._hits[ip].append(now)

        # Periodic cleanup to prevent unbounded growth
        self._check_count += 1
        if self._check_count >= self.cleanup_interval:
            self._check_count = 0
            self._cleanup_stale()
            self._evict_if_full()

    def reset(self) -> None:
        self._hits.clear()
        self._check_count = 0


# Pre-configured limiters for auth endpoints
login_limiter = RateLimiter(max_requests=5, window_seconds=60, name="login")
register_limiter = RateLimiter(max_requests=3, window_seconds=60, name="register")
password_reset_limiter = RateLimiter(
    max_requests=3,
    window_seconds=60,
    name="password_reset",
)

# Rate limiters for content creation endpoints
content_create_limiter = RateLimiter(max_requests=10, window_seconds=60, name="content_create")
comment_limiter = RateLimiter(max_requests=10, window_seconds=60, name="comment")
report_limiter = RateLimiter(max_requests=5, window_seconds=60, name="report")
like_limiter = RateLimiter(max_requests=30, window_seconds=60, name="like")


__all__ = [
    "RateLimiter",
    "comment_limiter",
    "content_create_limiter",
    "like_limiter",
    "login_limiter",
    "password_reset_limiter",
    "register_limiter",
    "report_limiter",
]
