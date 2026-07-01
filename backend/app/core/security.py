from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
import jwt

from .config import settings


def _prehash(password: str) -> bytes:
    """Pre-hash a password to a fixed length before bcrypt.

    bcrypt silently truncates input at 72 bytes, so two passwords sharing the
    first 72 bytes would authenticate identically (and the schema permits up to
    128-char passwords). SHA-256 collapses any length to 32 bytes; base64-encode
    to 44 bytes so the value stays well under bcrypt's limit. This must be
    applied symmetrically by both ``hash_password`` and ``verify_password``.
    """
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest)


def _classify_password(
    plain_password: str, hashed_password: str
) -> tuple[bool, bool]:
    """Return ``(matched, is_legacy)`` for a password against a stored hash.

    ``is_legacy`` is True only when the hash verifies via the old raw-bcrypt
    scheme (pre prehash rollout) — the signal ``login_user`` uses to transparently
    upgrade the stored hash on the next successful login.
    """
    stored = hashed_password.encode("utf-8")
    if bcrypt.checkpw(_prehash(plain_password), stored):
        return True, False
    if bcrypt.checkpw(plain_password.encode("utf-8"), stored):
        return True, True
    return False, False


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _classify_password(plain_password, hashed_password)[0]


def password_needs_rehash(plain_password: str, hashed_password: str) -> bool:
    """True if ``hashed_password`` is a legacy raw-bcrypt hash that should be
    re-hashed with the prehashed scheme. Assumes the password already verifies.
    """
    return _classify_password(plain_password, hashed_password)[1]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prehash(password), bcrypt.gensalt()).decode("utf-8")


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None, token_version: int = 0) -> str:
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode: dict[str, Any] = {"sub": subject, "exp": expire, "ver": token_version}
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])


def create_password_reset_token(email: str, token_version: int = 0) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    to_encode: dict[str, Any] = {
        "sub": email,
        "exp": expire,
        "type": "password_reset",
        "ver": token_version,
    }
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def verify_password_reset_token(token: str, token_version: Optional[int] = None) -> Optional[str]:
    try:
        payload = decode_token(token)
        if payload.get("type") != "password_reset":
            return None
        if token_version is not None and payload.get("ver", 0) != token_version:
            return None
        return payload.get("sub")
    except Exception:
        return None


__all__ = [
    "create_access_token",
    "decode_token",
    "hash_password",
    "password_needs_rehash",
    "verify_password",
    "create_password_reset_token",
    "verify_password_reset_token",
]
