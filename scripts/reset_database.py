
"""
Added a scripts/reset_database.py CLI that mirrors the proven --reset-db/--clear-uploads behaviors: it wires up repository helpers, initializes the DB, clears tables (optionally a subset), and wipes/recreates the upload directory. Use it via python scripts/reset_database.py with optional flags --skip-db, --skip-uploads, --no-recreate-uploads, or --tables turns chats ... for targeted clears.

Next steps: run python scripts/reset_database.py before local QA runs to start from a clean slate.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys
from typing import Sequence

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from EviQAsys.backend.app.env_setting import get_oceanbase_settings  # noqa: E402
from EviQAsys.backend.app.repositories import (  # noqa: E402
    DEFAULT_PURGE_ORDER,
    clear_tables,
    clear_upload_storage,
    initialize_database,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reset OceanBase tables and uploaded artifacts for a clean QA environment.",
    )
    parser.add_argument(
        "--tables",
        nargs="*",
        choices=DEFAULT_PURGE_ORDER,
        help=(
            "Optional subset of tables to clear (child tables first). "
            "Defaults to all in the recommended purge order."
        ),
    )
    parser.add_argument(
        "--skip-db",
        action="store_true",
        help="Skip clearing database tables.",
    )
    parser.add_argument(
        "--skip-uploads",
        action="store_true",
        help="Skip clearing uploaded files.",
    )
    parser.add_argument(
        "--no-recreate-uploads",
        action="store_true",
        help="Remove upload directory without recreating it.",
    )
    return parser.parse_args()


def reset_database(tables: Sequence[str] | None) -> None:
    initialize_database()
    settings = get_oceanbase_settings()
    print(
        f"[{datetime.utcnow()}] Clearing DB tables in {settings.default_database} "
        f"@ {settings.host}:{settings.port}",
    )
    clear_tables(tables=tables)
    print("Database tables cleared.")


def reset_upload_storage(recreate: bool) -> None:
    cleared_path = clear_upload_storage(recreate=recreate)
    action = "Cleared and recreated" if recreate else "Cleared"
    print(f"{action} upload directory at {cleared_path}")


def main() -> None:
    args = parse_args()
    tables = args.tables if args.tables else None

    if args.skip_db and args.skip_uploads:
        print("Nothing to do: both database and uploads were skipped.")
        return

    if not args.skip_db:
        reset_database(tables)
    else:
        print("Skipping database table reset.")

    if not args.skip_uploads:
        reset_upload_storage(recreate=not args.no_recreate_uploads)
    else:
        print("Skipping upload directory cleanup.")

    print("Reset complete.")


if __name__ == "__main__":
    main()
