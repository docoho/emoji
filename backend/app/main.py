from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from .api import router as api_router
from .core.config import settings
from .core.redis_client import validate_redis_connection
from .db import run_alembic_upgrade


@asynccontextmanager
async def lifespan(app: FastAPI):
    import logging
    logger = logging.getLogger(__name__)
    validate_redis_connection()
    run_alembic_upgrade()
    _enforce_required_secrets(logger)
    yield


def _enforce_required_secrets(logger) -> None:
    """In production, missing SECRET_KEY / OAUTH_STATE_SECRET aborts startup.

    In development, settings.model_post_init has already auto-generated any
    missing secrets, so this check passes silently after logging a warning.
    """
    missing = [
        name for name, value in (
            ("SECRET_KEY", settings.secret_key),
            ("OAUTH_STATE_SECRET", settings.oauth_state_secret),
        ) if not value
    ]
    if not missing:
        if settings.environment != "production":
            logger.info(
                "Running in %s mode with auto-generated secrets — JWTs will "
                "invalidate on restart. Set SECRET_KEY in .env for stable sessions.",
                settings.environment,
            )
        return
    if settings.environment == "production":
        raise RuntimeError(
            f"Missing required secret(s) in production: {', '.join(missing)}"
        )
    logger.warning(
        "Missing secret(s): %s — auto-generation should have populated these "
        "in development; check Settings.model_post_init.",
        ", ".join(missing),
    )


def create_app() -> FastAPI:
    app = FastAPI(title="Emoji Credentials API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next) -> Response:  # type: ignore[type-arg]
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        # HSTS pins HTTPS for two years. The app is deployed over TLS at
        # emoji.undov.com; this header is only honored by browsers over HTTPS,
        # so it is harmless (and ignored) on local http://localhost dev.
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains"
        )
        # style-src keeps 'unsafe-inline' because the Vue frontend uses :style
        # bindings (EmojiCard, EmojiGrid, UserProfileView, AdminDashboardView,
        # HomeView) which emit inline style attributes at runtime. Dropping it
        # would break those components — verify by grepping :style and style=""
        # before considering removal.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' https:; "
            "connect-src 'self' https://accounts.google.com; "
            "frame-ancestors 'none'"
        )
        return response

    return app


app = create_app()
