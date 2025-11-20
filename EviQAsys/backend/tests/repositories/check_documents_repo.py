from __future__ import annotations

from datetime import datetime

from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.append(str(PROJECT_ROOT))

from EviQAsys.backend.app.env_setting import get_oceanbase_settings
from EviQAsys.backend.app.repositories import (
    CollectionsRepository,
    DocumentsRepository,
    initialize_database,
)


def main() -> None:
    settings = get_oceanbase_settings()
    print("== Documents Repository Manual Check ==")
    print(f"[{datetime.utcnow()}] Target DB: {settings.default_database} @ {settings.host}:{settings.port}")

    print("Ensuring schema is applied...")
    initialize_database()

    collections_repo = CollectionsRepository()
    documents_repo = DocumentsRepository()

    collection = collections_repo.create_collection(name="manual-doc-check", description="Temp collection for document script.")
    print(f"Temporary collection: {collection}")
    document = {}

    try:
        document = documents_repo.create_document(
            collection_id=collection["id"],
            title="Manual Repo Test",
            file_name="manual.pdf",
            file_path="/tmp/manual.pdf",
            file_sha256="manual-hash",
            file_size_bytes=1234,
            num_pages=1,
            md_text="# Manual Repo Test",
            element_count=0,
        )
        print(f"Created document: {document}")

        print("Listing documents for the temp collection...")
        docs = documents_repo.list_by_collection(collection["id"])
        for doc in docs:
            print(f"  - {doc['id']}: {doc.get('title')} (pages={doc.get('num_pages')})")

        print("Updating document metadata...")
        documents_repo.update_document(
            document["id"],
            title="Manual Repo Test (updated)",
            num_pages=2,
            element_count=5,
            abstract="Manual abstract content for repository check.",
            meta_info={"updated_by": "check_documents_repo", "purpose": "manual verification"},
        )
        refreshed = documents_repo.get_by_id(document["id"])
        print(f"Updated document: {refreshed}")

    finally:
        if document.get("id"):
            print("Cleaning up document row...")
            documents_repo.delete_document(document["id"])
        print("Deleting temporary collection...")
        collections_repo.delete_collection(collection["id"])

    print("Document repository check completed.")


if __name__ == "__main__":
    main()
