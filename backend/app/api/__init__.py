from fastapi import APIRouter


router = APIRouter(prefix="/api")


def include_routes() -> None:
    from . import routes

    router.include_router(routes.router)


include_routes()


__all__ = ["router"]
