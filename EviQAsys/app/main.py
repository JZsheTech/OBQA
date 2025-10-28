"""FastAPI application factory."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.api import api_router
from app.core.config import settings
from app.db import init_database_schema


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Initialise database schema on startup."""
    init_database_schema()
    yield


def create_app() -> FastAPI:
    """Construct the FastAPI application."""
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(api_router)
    return app


app = create_app()
