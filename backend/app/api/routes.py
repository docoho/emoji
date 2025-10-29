from fastapi import APIRouter

from .endpoints import auth, emojis

router = APIRouter()
router.include_router(auth.router)
router.include_router(emojis.router)


@router.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


__all__ = ["router"]
