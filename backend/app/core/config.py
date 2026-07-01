import secrets
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


def _generate_secret() -> str:
    return secrets.token_urlsafe(32)


class Settings(BaseSettings):
    environment: Literal["development", "production"] = "development"
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    database_url: str = "sqlite:///./app.db"
    cors_origins: list[str] = ["http://localhost:5173"]
    redis_url: str = ""
    trusted_proxy_ips: list[str] = ["127.0.0.1", "::1"]

    # Google OAuth2
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/auth/oauth/google/callback"
    oauth_state_secret: str = ""
    frontend_url: str = "http://localhost:5173"

    # MailerSend email (HTTP API — SMTP ports are commonly blocked)
    mailersend_api_key: str = ""
    mail_from: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def model_post_init(self, __context: object) -> None:
        # In development, auto-generate any missing secrets so a fresh checkout
        # can run `make backend` without configuration. In production, leave them
        # empty so the lifespan startup check fails loudly with a clear message.
        if self.environment == "development":
            if not self.secret_key:
                self.secret_key = _generate_secret()
            if not self.oauth_state_secret:
                self.oauth_state_secret = _generate_secret()


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


__all__ = ["Settings", "get_settings", "settings"]
