from __future__ import annotations

from datetime import datetime

import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.append(str(PROJECT_ROOT))

from EviQAsys.backend.app.env_setting import get_oceanbase_settings
from EviQAsys.backend.app.repositories import CollectionsRepository, initialize_database


def main() -> None:
    settings = get_oceanbase_settings()
    print("== Collection Repository Manual Check ==")
    print(f"[{datetime.utcnow()}] Target DB: {settings.default_database} @ {settings.host}:{settings.port}")

    print("Initializing schema (idempotent)...")
    initialize_database()

    repo = CollectionsRepository()
    print("Existing collections:")
    for row in repo.list_collections():
        print(f"  - {row['id']}: {row['name']} ({row.get('created_at')})")

    print("Creating a sample collection...")
    created = repo.create_collection(name="manual-check", description="Temp collection for repository check.")
    print(f"Created row: {created}")

    fetched = repo.get_by_id(created["id"])
    print(f"Fetched by ID: {fetched}")

    print("Updating description...")
    repo.update_collection(created["id"], description="Updated via manual test script.")
    updated = repo.get_by_id(created["id"])
    print(f"Updated row: {updated}")

    print("Cleaning up inserted collection...")
    repo.delete_collection(created["id"])
    print("Cleanup complete.")


if __name__ == "__main__":
    main()
