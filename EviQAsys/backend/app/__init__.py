"""Backend application package for the OBQA demo system."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - hints for static checkers only
    from fastapi import FastAPI

__all__ = ["create_app"]


def create_app():
    """Import and instantiate the FastAPI application lazily."""

    from .main import create_app as _create_app

    return _create_app()
