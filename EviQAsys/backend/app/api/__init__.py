from fastapi import APIRouter

from .routes.chats import router as chats_router
from .routes.collections import router as collections_router
from .routes.debug import router as debug_router
from .routes.documents import router as documents_router
from .routes.retrieval import router as retrieval_router

api_router = APIRouter(prefix="/api")
api_router.include_router(collections_router)
api_router.include_router(documents_router)
api_router.include_router(retrieval_router)
api_router.include_router(chats_router)
api_router.include_router(debug_router)

__all__ = ["api_router"]
