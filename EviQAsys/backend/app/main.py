from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import api_router
from .repositories import initialize_database

logger = logging.getLogger(__name__)


def _create_app() -> FastAPI:
    app = FastAPI(title="EviQAsys API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def startup_event() -> None:
        try:
            initialize_database()
        except Exception as exc:  # pragma: no cover - startup failure path
            logger.exception("OceanBase initialization failed.")
            raise RuntimeError("Database initialization failed.") from exc

    app.include_router(api_router)

    @app.get("/healthz")
    async def health_check() -> dict[str, bool]:
        return {"ok": True}

    return app


app = _create_app()
