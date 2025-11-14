#  python EviQAsys/backend/tests/manual/test_m3_e2e_in_collection_multidoc_parse_and_query.py --query "What is reinforcement learning?"

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.append(str(PROJECT_ROOT))

from EviQAsys.backend.app.env_setting import get_oceanbase_settings  # noqa: E402
from EviQAsys.backend.app.repositories import (  # noqa: E402
    CollectionsRepository,
    DocumentsRepository,
    ElementsRepository,
    clear_tables,
    clear_upload_storage,
    initialize_database,
)
from EviQAsys.backend.app.services.embedding import EmbeddingService  # noqa: E402
from EviQAsys.backend.app.services.ingestion.document_ingestor import (  # noqa: E402
    DocumentIngestor,
    DuplicateDocumentError,
)
from EviQAsys.backend.app.services.retrieval import Retriever  # noqa: E402

DEFAULT_PDF_DIR = PROJECT_ROOT / "sample_data" / "pdf_doc" / "RL_paper_small"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "M3 manual e2e: ingest multiple PDFs into a single collection, "
            "embed elements, then run semantic and full-text retrieval."
        ),
    )
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        default=DEFAULT_PDF_DIR,
        help="Directory containing PDF files to ingest.",
    )
    parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="Query text used for both retrieval modes.",
    )
    parser.add_argument("--top-k", type=int, default=5, help="Number of results to print per retrieval mode.")
    parser.add_argument(
        "--elem-types",
        type=str,
        default=None,
        help="Comma separated element types filter (e.g. text,header).",
    )
    parser.add_argument(
        "--collection-name",
        type=str,
        default="manual-m3-e2e-multidoc",
        help="Collection name to create for this run.",
    )
    parser.add_argument(
        "--embed-batch-size",
        type=int,
        default=16,
        help="Batch size when requesting embeddings.",
    )
    parser.add_argument(
        "--search-modes",
        nargs="+",
        choices=["vector", "fulltext"],
        default=["vector", "fulltext"],
        help="Retrieval modes to execute.",
    )
    parser.add_argument("--keep", action="store_true", help="Keep created rows (skip cleanup).")
    parser.add_argument("--reset-db", action="store_true", help="Clear tables before running.")
    parser.add_argument("--clear-uploads", action="store_true", help="Clear UPLOAD_DIR before running.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pdf_dir = args.pdf_dir.expanduser().resolve()
    if not pdf_dir.exists():
        raise FileNotFoundError(f"PDF directory not found: {pdf_dir}")
    pdf_paths = sorted(path for path in pdf_dir.iterdir() if path.is_file() and path.suffix.lower() == ".pdf")
    if not pdf_paths:
        raise RuntimeError(f"No PDF files found under {pdf_dir}")

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
    embedding_service = EmbeddingService()
    retriever = Retriever(embedding_service=embedding_service, elements_repo=elements_repo)

    settings = get_oceanbase_settings()
    print(f"[{datetime.utcnow()}] Target DB: {settings.default_database} @ {settings.host}:{settings.port}")
    print(f"Preparing to ingest {len(pdf_paths)} PDFs from {pdf_dir}")
    for idx, pdf in enumerate(pdf_paths, start=1):
        print(f"  {idx}. {pdf.name}")

    print("Creating collection for multi-document e2e run...")
    collection = collections_repo.create_collection(
        name=args.collection_name,
        description="Manual M3 e2e ingest (multi-doc) + dual-mode retrieval verification.",
    )
    print(f"Collection created: {collection}")

    ingested_doc_ids: list[int] = []
    try:
        for pdf_path in pdf_paths:
            document = ingest_document(ingestor, elements_repo, collection["id"], pdf_path)
            ingested_doc_ids.append(document["id"])
            print(
                f"Document stored id={document['id']} "
                f"(elements={document.get('element_count')}), file='{pdf_path.name}'",
            )
            embedded = embed_document_elements(
                repo=elements_repo,
                service=embedding_service,
                collection_id=collection["id"],
                doc_id=document["id"],
                batch_size=args.embed_batch_size,
            )
            print(f"Embedding completed for {embedded} elements (doc_id={document['id']}).")

        elem_types = parse_elem_types(args.elem_types)
        for mode in args.search_modes:
            print("=" * 80)
            run_retrieval(
                retriever=retriever,
                collection_id=collection["id"],
                query=args.query,
                top_k=args.top_k,
                elem_types=elem_types,
                doc_id=None,  # search across the entire collection
                search_mode=mode,
            )
        print("=" * 80)
        print("Retrieval completed for all requested modes.")
    finally:
        if not args.keep:
            print("Cleaning up inserted documents and collection...")
            for doc_id in ingested_doc_ids:
                documents_repo.delete_document(doc_id)
            collections_repo.delete_collection(collection["id"])
            print("Cleanup complete.")
        else:
            print("Keep flag enabled; skipping cleanup.")


def ingest_document(
    ingestor: DocumentIngestor,
    elements_repo: ElementsRepository,
    collection_id: int,
    pdf_path: Path,
) -> dict[str, object]:
    print(f"[{datetime.utcnow()}] Ingesting PDF: {pdf_path}")
    try:
        document = ingestor.ingest_path(collection_id, pdf_path)
    except DuplicateDocumentError as exc:
        raise RuntimeError(f"Duplicate detected for collection {collection_id}: {exc}") from exc

    elements = elements_repo.list_by_document(document["id"])
    type_counter = Counter(element["elem_type"] for element in elements)
    print(f"Stored elements: {len(elements)}")
    for elem_type, count in sorted(type_counter.items()):
        print(f"  - {elem_type}: {count}")
    if elements:
        preview = elements[0]
        print("Sample element preview:")
        print(f"    elem_type = {preview.get('elem_type')}")
        print(f"    header_name = {preview.get('header_name')}")
        print(f"    page_no = {preview.get('page_no')}")
        print(f"    has_image = {'yes' if preview.get('image_base64') else 'no'}")
    return document


def embed_document_elements(
    *,
    repo: ElementsRepository,
    service: EmbeddingService,
    collection_id: int,
    doc_id: int,
    batch_size: int,
) -> int:
    total_embedded = 0
    batch_size = max(1, batch_size)
    while True:
        pending = repo.list_unembedded(
            collection_id=collection_id,
            doc_id=doc_id,
            limit=batch_size,
        )
        if not pending:
            break
        payload = service.batch_embed_elements(pending)
        repo.update_embeddings(payload)
        total_embedded += len(payload)
        vector_dim = len(next(iter(payload.values())))
        print(
            f"[{datetime.utcnow()}] Embedded batch size={len(payload)} "
            f"(sample element id={next(iter(payload.keys()))}, dim={vector_dim})",
        )
    return total_embedded


def run_retrieval(
    *,
    retriever: Retriever,
    collection_id: int,
    query: str,
    top_k: int,
    elem_types: list[str] | None,
    doc_id: int | None,
    search_mode: str,
) -> None:
    print(
        f"[{datetime.utcnow()}] Running retrieval (collection={collection_id}, "
        f"doc_id={doc_id}, mode={search_mode}, top_k={top_k})",
    )
    start = time.perf_counter()
    results = retriever.retrieve_topk(
        collection_id=collection_id,
        query_text=query,
        top_k=top_k,
        doc_id=doc_id,
        elem_types=elem_types,
        search_mode=search_mode,
    )
    elapsed = (time.perf_counter() - start) * 1000
    print(f"Retrieval finished in {elapsed:.1f} ms; results={len(results)}")
    if not results:
        print("No candidates returned.")
        return
    for idx, item in enumerate(results, start=1):
        bbox = item.get("bbox")
        snippet = (item.get("text_content") or "").strip()
        print(
            f"{idx}. element_id={item['element_id']} doc_id={item['doc_id']} "
            f"type={item['elem_type']} page={item.get('page_no')} score={item['score']:.4f} "
            f"bbox={bbox}",
        )
        if snippet:
            print(f"   text: {snippet[:200]}")


def parse_elem_types(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    values = [entry.strip() for entry in raw.split(",") if entry.strip()]
    return values or None


if __name__ == "__main__":
    main()
