#!/usr/bin/env python3
"""
Reset OceanBase schema for OBQA:

- Drops ALL tables in the target database (disabling foreign key checks)
- Recreates tables using the current DDL in repositories/sql/schema.sql

Usage:
  python scripts/reset_database.py           # prompts for confirmation
  python scripts/reset_database.py --yes     # no prompt
"""

from __future__ import annotations

import argparse
import sys
from typing import Iterable

from sqlalchemy import text

from EviQAsys.backend.app.env_setting import get_oceanbase_settings
from EviQAsys.backend.app.repositories.db import get_engine, initialize_database


def _list_tables(schema_name: str) -> list[str]:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(f"USE `{schema_name}`"))
        result = conn.execute(
            text(
                "SELECT TABLE_NAME FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = :schema",
            ),
            {"schema": schema_name},
        )
        return [row[0] for row in result]


def _drop_tables(schema_name: str, tables: Iterable[str]) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(f"USE `{schema_name}`"))
        # Disable FK checks for drop ordering simplicity.
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in tables:
            conn.execute(text(f"DROP TABLE IF EXISTS `{table}`"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Drop all tables and recreate schema.")
    parser.add_argument(
        "--yes",
        dest="assume_yes",
        action="store_true",
        help="Proceed without confirmation.",
    )
    args = parser.parse_args(argv)

    settings = get_oceanbase_settings()
    schema = settings.default_database
    tables = _list_tables(schema)
    if not args.assume_yes:
        print(f"This will DROP and RECREATE all tables in database '{schema}'.")
        print(f"Tables to drop: {', '.join(tables) if tables else '(none)'}")
        confirm = input("Type 'yes' to continue: ").strip().lower()
        if confirm != "yes":
            print("Abort.")
            return 1

    print(f"Dropping {len(tables)} tables from '{schema}'...")
    _drop_tables(schema, tables)
    print("Re-initializing schema...")
    initialize_database()
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

