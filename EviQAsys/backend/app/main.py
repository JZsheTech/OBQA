"""FastAPI application setup with route registration."""

from fastapi import FastAPI

from .api.routes import collections, documents, chats


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance.

    The app exposes contract-first routes covering collection management,
    document ingestion, indexing triggers, and chat-based QA interactions.
    Business logic is intentionally stubbed during Milestone 2 so that
    interface expectations remain explicit and easy to test.
    """

    app = FastAPI(
        title="OBQA Demo Backend",
        description=(
            "Milestone 2 skeleton exposing collection, document, indexing, "
            "and QA chat interfaces."
        ),
        version="0.1.0",
    )

    app.include_router(collections.router)
    app.include_router(documents.router)
    app.include_router(chats.router)

    return app


app = create_app()
