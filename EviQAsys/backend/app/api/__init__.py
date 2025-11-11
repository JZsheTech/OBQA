from fastapi import APIRouter

from .routes.collections import router as collections_router

api_router = APIRouter(prefix="/api")
api_router.include_router(collections_router)

__all__ = ["api_router"]
