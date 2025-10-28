"""API router aggregation."""

from fastapi import APIRouter

from .routes import chats, collections, documents, elements, search, turns

api_router = APIRouter()

api_router.include_router(collections.router)
api_router.include_router(documents.router)
api_router.include_router(elements.router)
api_router.include_router(chats.router)
api_router.include_router(turns.router)
api_router.include_router(search.router)

__all__ = ["api_router"]
