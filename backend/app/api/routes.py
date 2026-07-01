from fastapi import APIRouter

from .endpoints import admin, auth, collections, comments, creator, emojis, oauth, users

router = APIRouter()
router.include_router(auth.router)
router.include_router(oauth.router)
router.include_router(admin.router)
router.include_router(collections.router)
router.include_router(comments.router)
router.include_router(creator.router)
router.include_router(emojis.router)
router.include_router(users.router)


@router.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


__all__ = ["router"]
