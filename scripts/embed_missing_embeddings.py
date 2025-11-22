"""
Embed pending elements (vec_embedding is NULL) for a collection or a specific document.
Run manually, e.g.:
  python scripts/embed_missing_embeddings.py --collection-id 3
  python scripts/embed_missing_embeddings.py --collection-id 3 --doc-id 12 --batch-size 16
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from EviQAsys.backend.app.env_setting import get_oceanbase_settings  # noqa: E402
from EviQAsys.backend.app.repositories import initialize_database  # noqa: E402
from EviQAsys.backend.app.services.index import DocumentIndexer  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill embeddings for documents by embedding elements without vec_embedding.",
    )
    parser.add_argument("--collection-id", "-c", dest="collection_id", type=int, required=True, help="Target collection id.")
    parser.add_argument("--doc-id", "-d", dest="doc_id", type=int, help="Optional document id to scope embedding.")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Embedding batch size (matches API background embedding defaults).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    initialize_database()
    settings = get_oceanbase_settings()
    print(
        f"[{datetime.utcnow()}] Embedding pending elements in {settings.default_database} "
        f"@ {settings.host}:{settings.port}",
    )
    indexer = DocumentIndexer(batch_size=args.batch_size)

    if args.doc_id:
        embedded = indexer.embed_document(
            collection_id=args.collection_id,
            doc_id=args.doc_id,
            batch_size=args.batch_size,
        )
        scope_label = f"doc_id={args.doc_id}"
    else:
        embedded = indexer.embed_collection(
            collection_id=args.collection_id,
            batch_size=args.batch_size,
        )
        scope_label = f"collection_id={args.collection_id}"

    print(f"Embedding complete ({scope_label}); embedded elements: {embedded}")
    if embedded == 0:
        print("No pending elements were found. If expected, verify the collection/document ids or ingestion status.")


if __name__ == "__main__":
    main()
