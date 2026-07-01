from .admin import router as admin_router
from .auth import router as auth_router
from .comments import router as comments_router
from .collections import router as collections_router
from .creator import router as creator_router
from .emojis import router as emojis_router

__all__ = [
    "admin_router",
    "auth_router",
    "comments_router",
    "collections_router",
    "creator_router",
    "emojis_router",
]
