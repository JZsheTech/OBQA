# usage : python EviQAsys/backend/tests/manual/test_m2_ingest.py 

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
from pathlib import Path

PROJECT_ROOT_DIR = Path(__file__).resolve().parents[4]
import sys
sys.path.append(str(PROJECT_ROOT_DIR))


from EviQAsys.backend.app.env_setting import get_oceanbase_settings
from EviQAsys.backend.app.repositories import CollectionsRepository, initialize_database

from EviQAsys.backend.app.repositories import (
    DocumentsRepository,
    ElementsRepository,
    initialize_database,
)
from EviQAsys.backend.app.services.ingestion.document_ingestor import DocumentIngestor, DuplicateDocumentError

DEFAULT_PDF = Path(__file__).resolve().parents[4] / "sample_data" / "pdf_doc" / "1-Cui et al. - 2019 - Class-Balanced Loss Based on Effective Number of Samples.pdf"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manual MinerU ingestion smoke test.")

    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF, help="Path to a real PDF file for ingestion.")
    parser.add_argument("--keep", action="store_true", help="Keep the ingested rows instead of cleaning up.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    initialize_database()
    ingestor = DocumentIngestor()
    documents_repo = DocumentsRepository()
    elements_repo = ElementsRepository()
    print(f"[{datetime.utcnow()}] Starting ingestion for collection=manual-check, pdf={args.pdf}")
    print(f"Using PDF: {args.pdf}")

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


    if not args.pdf.exists():
        raise FileNotFoundError(f"PDF not found: {args.pdf}")

    document: dict[str, object] | None = None
    try:
        document = ingestor.ingest_path(created["id"], args.pdf)
    except DuplicateDocumentError as exc:
        print(f"Duplicate detected: {exc}")
        return

    assert document is not None
    print(f"Document created: id={document['id']} size={document.get('file_size_bytes')} bytes")
    elements = elements_repo.list_by_document(document["id"])
    print(f"Stored elements: {len(elements)}")
    type_counter = Counter(element["elem_type"] for element in elements)
    for elem_type, count in sorted(type_counter.items()):
        print(f"  - {elem_type}: {count}")
    if elements:
        sample = elements[0]
        print("Sample element:")
        print(f"    level_nav = {sample.get('level_nav')}")
        print(f"    header_name = {sample.get('header_name')}")
        print(f"    page_no = {sample.get('page_no')}")
        print(f"    bbox_json = {sample.get('bbox_json')}")

    if not args.keep and document:
        print("Cleaning up inserted document for manual test...")
        documents_repo.delete_document(document["id"])
        print("Cleanup completed.")
        print("Cleaning up inserted collection...")
        repo.delete_collection(created["id"])
        print("Cleanup complete.")

if __name__ == "__main__":
    main()
