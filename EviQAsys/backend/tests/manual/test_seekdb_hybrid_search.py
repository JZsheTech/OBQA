# python EviQAsys/backend/tests/manual/test_seekdb_hybrid_search.py --question "Summarize the key contributions."

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys
import textwrap

PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.append(str(PROJECT_ROOT))

from EviQAsys.backend.app.env_setting import (  # noqa: E402
    HYBRID_SEARCH_BACKEND,
    HYBRID_TEXT_BOOST,
    HYBRID_VECTOR_BOOST,
    get_oceanbase_settings,
)
from EviQAsys.backend.app.repositories import (  # noqa: E402
    CollectionsRepository,
    DocumentsRepository,
    ElementsRepository,
    clear_tables,
    clear_upload_storage,
    initialize_database,
)
from EviQAsys.backend.app.services.ingestion.document_ingestor import (  # noqa: E402
    DocumentIngestor,
    DuplicateDocumentError,
)
from EviQAsys.backend.app.services.index.document_indexer import DocumentIndexer  # noqa: E402
from EviQAsys.backend.app.services.retrieval.retriever import Retriever  # noqa: E402

DEFAULT_PDF_DIR = PROJECT_ROOT / "sample_data" / "pdf_doc" / "RL_paper_small"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Manual seekdb hybrid search test: ingest PDFs, build chunks, then run hybrid retrieval. "
            "Use a non-production database and real PDFs."
        ),
    )
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        default=DEFAULT_PDF_DIR,
        help="Directory that stores PDF files for ingestion.",
    )
    parser.add_argument(
        "--question",
        type=str,
        required=True,
        help="User question for hybrid search.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=8,
        help="Top-k results to return.",
    )
    parser.add_argument(
        "--collection-name",
        type=str,
        default="manual-seekdb-hybrid",
        help="Collection name for this run.",
    )
    parser.add_argument(
        "--collection-id",
        type=int,
        help="Reuse an existing collection id to skip ingestion.",
    )
    parser.add_argument(
        "--embed-batch-size",
        type=int,
        default=16,
        help="Batch size for embedding requests.",
    )
    parser.add_argument(
        "--skip-index",
        action="store_true",
        help="Skip chunk rebuild/embedding when reusing collection id.",
    )
    parser.add_argument("--keep", action="store_true", help="Keep created rows for inspection.")
    parser.add_argument("--reset-db", action="store_true", help="Clear database tables before running.")
    parser.add_argument("--clear-uploads", action="store_true", help="Clear UPLOAD_DIR before running.")
    return parser.parse_args()


def ensure_pdfs(pdf_dir: Path) -> list[Path]:
    pdf_dir = pdf_dir.expanduser().resolve()
    if not pdf_dir.exists():
        raise FileNotFoundError(f"PDF directory not found: {pdf_dir}")
    pdf_paths = sorted(path for path in pdf_dir.iterdir() if path.is_file() and path.suffix.lower() == ".pdf")
    if not pdf_paths:
        raise RuntimeError(f"No PDF files found under {pdf_dir}")
    return pdf_paths


def main() -> None:
    args = parse_args()
    if args.collection_id is not None and args.reset_db:
        raise ValueError("Cannot combine --collection-id with --reset-db; the reset would drop the collection.")

    reusing_collection = args.collection_id is not None
    pdf_paths: list[Path] = []
    if not reusing_collection:
        pdf_paths = ensure_pdfs(args.pdf_dir)

    initialize_database()
    if args.reset_db:
        print("Clearing database tables before ingestion...")
        clear_tables()
    if args.clear_uploads:
        cleared = clear_upload_storage()
        print(f"Cleared upload directory: {cleared}")

    collections_repo = CollectionsRepository()
    documents_repo = DocumentsRepository()
    elements_repo = ElementsRepository()
    ingestor = DocumentIngestor()
    indexer = DocumentIndexer()
    retriever = Retriever()

    settings = get_oceanbase_settings()
    print(
        f"[{datetime.utcnow()}] Target DB: {settings.default_database} @ {settings.host}:{settings.port} "
        f"(hybrid_backend={HYBRID_SEARCH_BACKEND}, text_boost={HYBRID_TEXT_BOOST}, "
        f"vector_boost={HYBRID_VECTOR_BOOST})",
    )

    created_collection = False
    collection: dict[str, object] | None = None
    if reusing_collection:
        collection = collections_repo.get_by_id(args.collection_id)
        if not collection:
            raise RuntimeError(f"Collection id={args.collection_id} not found.")
        print(f"Reusing collection id={collection['id']} name={collection['name']}; skipping ingestion.")
    else:
        print(f"Preparing to ingest {len(pdf_paths)} PDFs from {args.pdf_dir}")
        for idx, pdf in enumerate(pdf_paths, start=1):
            print(f"  {idx}. {pdf.name}")

        collection = collections_repo.create_collection(
            name=args.collection_name,
            description="Manual seekdb hybrid search validation.",
        )
        created_collection = True
        print(f"Collection created id={collection['id']}")

    ingested_doc_ids: list[int] = []
    try:
        if not reusing_collection:
            for pdf in pdf_paths:
                document = ingest_document(ingestor, elements_repo, collection["id"], pdf)
                ingested_doc_ids.append(document["id"])
                indexed = indexer.embed_document(
                    collection_id=collection["id"],
                    doc_id=document["id"],
                    batch_size=args.embed_batch_size,
                )
                print(f"Indexed+embedded {indexed} chunks for doc_id={document['id']}.")
        else:
            if not args.skip_index:
                indexed = indexer.embed_collection(
                    collection_id=collection["id"],
                    batch_size=args.embed_batch_size,
                )
                print(f"Indexed+embedded {indexed} chunks for collection_id={collection['id']}.")
            else:
                print("Skipping chunk rebuild/embedding as requested.")

        print("=" * 80)
        print(f"Hybrid retrieval query: {args.question}")
        rows = retriever.retrieve_topk(
            collection_id=collection["id"],
            query_text=args.question,
            top_k=args.top_k,
            search_mode="hybrid",
        )
        print(f"Returned {len(rows)} rows (top_k={args.top_k}).")
        for idx, row in enumerate(rows, start=1):
            snippet = (row.get("chunk_text_main") or "").strip().replace("\n", " ")
            snippet = textwrap.shorten(snippet, width=200, placeholder="...")
            score = row.get("score")
            score_text = f"{float(score):.6f}" if score is not None else "None"
            print(
                f"[{idx:02d}] chunk_id={row.get('chunk_id')} score={score_text} "
                f"doc_id={row.get('doc_id')} type={row.get('chunk_type')} "
                f"text={snippet}"
            )
        print("=" * 80)
        print("Manual inspection checklist:")
        print("- Scores are present and sorted descending")
        print("- Top results are semantically related to the query")
        print("- If fewer than top_k results are returned, confirm filters/indexes")
    finally:
        if not args.keep:
            print("Cleaning up created documents/collection...")
            if created_collection and collection:
                for doc_id in ingested_doc_ids:
                    documents_repo.delete_document(doc_id)
                collections_repo.delete_collection(collection["id"])
            elif collection:
                print(f"Reused collection id={collection['id']}; leaving it intact.")
            print("Cleanup complete.")
        else:
            if collection:
                print(
                    f"Keep flag enabled; collection_id={collection['id']} remains available. "
                    f"Re-run with --collection-id {collection['id']} to reuse indexed documents.",
                )
            else:
                print("Keep flag enabled; leaving data in place.")


def ingest_document(
    ingestor: DocumentIngestor,
    elements_repo: ElementsRepository,
    collection_id: int,
    pdf_path: Path,
) -> dict[str, object]:
    print(f"[{datetime.utcnow()}] Ingesting PDF: {pdf_path.name}")
    try:
        document = ingestor.ingest_path(collection_id, pdf_path)
    except DuplicateDocumentError as exc:
        raise RuntimeError(f"Duplicate detected for collection {collection_id}: {exc}") from exc

    element_count = len(elements_repo.list_by_document(document["id"]))
    print(f"Ingested doc_id={document['id']} elements={element_count}")
    return document


if __name__ == "__main__":
    main()
