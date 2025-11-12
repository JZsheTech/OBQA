from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Iterable, Sequence

from sqlalchemy import text

from ..env_setting import UploadSettings, get_upload_settings
from .db import db_connection

logger = logging.getLogger(__name__)

DEFAULT_PURGE_ORDER: tuple[str, ...] = (
    "turn2evidence",
    "turns",
    "chats",
    "elements",
    "documents",
    "collections",
)


def clear_tables(tables: Sequence[str] | None = None) -> None:
    """Delete all rows from the selected tables (child tables first)."""
    target_tables = list(tables) if tables else list(DEFAULT_PURGE_ORDER)
    logger.info("Clearing tables: %s", ", ".join(target_tables))
    with db_connection() as connection:
        for table in target_tables:
            connection.execute(text(f"DELETE FROM `{table}`"))


def clear_upload_storage(*, recreate: bool = True, upload_settings: UploadSettings | None = None) -> Path:
    """Remove all persisted upload artifacts under UPLOAD_DIR."""
    settings = upload_settings or get_upload_settings()
    root = Path(settings.root_dir)
    if root.exists():
        shutil.rmtree(root)
        logger.info("Removed upload storage at %s", root)
    if recreate:
        root.mkdir(parents=True, exist_ok=True)
        logger.info("Re-created upload directory at %s", root)
    return root


__all__ = ["clear_tables", "clear_upload_storage", "DEFAULT_PURGE_ORDER"]
