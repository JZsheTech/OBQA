from fastapi import APIRouter

from .routes.collections import router as collections_router
from .routes.retrieval import router as retrieval_router
from .routes.chats import router as chats_router

api_router = APIRouter(prefix="/api")
api_router.include_router(collections_router)
api_router.include_router(retrieval_router)
api_router.include_router(chats_router)

__all__ = ["api_router"]
