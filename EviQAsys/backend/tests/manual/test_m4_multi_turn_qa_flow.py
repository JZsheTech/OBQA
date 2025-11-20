#  python EviQAsys/backend/tests/manual/test_m4_multi_turn_qa_flow.py --question "First question" --question "Follow-up question"

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.append(str(PROJECT_ROOT))

from EviQAsys.backend.app.env_setting import get_oceanbase_settings  # noqa: E402
from EviQAsys.backend.app.repositories import (  # noqa: E402
    ChatsRepository,
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
)
from EviQAsys.backend.app.services.qa_flow import run_qa_turn  # noqa: E402
from test_m4_qa_flow import (  # noqa: E402
    DEFAULT_PDF_DIR,
    embed_document_elements,
    ensure_pdfs,
    ingest_document,
    print_evidences as print_single_turn_evidences,
    print_rendered_answer,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Manual multi-turn QA flow: optionally ingest + embed PDF elements, "
            "reuse an existing collection, then run repeated questions on the same chat."
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
        dest="questions",
        action="append",
        required=True,
        help="User question sent to the QA flow; specify one --question per turn (>=2 for multi-turn).",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=8,
        help="Retrieval TopK for QA orchestrator.",
    )
    parser.add_argument(
        "--enable-image-vqa",
        action="store_true",
        help="Enable the optional visual question answering path.",
    )
    parser.add_argument(
        "--enable-memory-summarizer",
        action="store_true",
        help="Enable the DSPy MemorySummarizer for chat history (disabled by default).",
    )
    parser.add_argument(
        "--collection-name",
        type=str,
        default="manual-m4-multi-turn-qa-flow",
        help="Collection name for this run (used only when creating a new collection).",
    )
    parser.add_argument(
        "--collection-id",
        type=int,
        help="Reuse an existing collection id to skip ingestion and indexing.",
    )
    parser.add_argument(
        "--embed-batch-size",
        type=int,
        default=16,
        help="Batch size for embedding requests.",
    )
    parser.add_argument("--keep", action="store_true", help="Keep created rows for inspection.")
    parser.add_argument("--reset-db", action="store_true", help="Clear database tables before running.")
    parser.add_argument("--clear-uploads", action="store_true", help="Clear UPLOAD_DIR before running.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if len(args.questions) < 2:
        raise ValueError("Provide at least two --question arguments to exercise multi-turn flows.")
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
    chats_repo = ChatsRepository()
    ingestor = DocumentIngestor()
    embedding_service = EmbeddingService()

    settings = get_oceanbase_settings()
    print(f"[{datetime.utcnow()}] Target DB: {settings.default_database} @ {settings.host}:{settings.port}")
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
            description="Manual M4 multi-turn QA flow validation.",
        )
        created_collection = True
        print(f"Collection created id={collection['id']}")

    ingested_doc_ids: list[int] = []
    chat: dict[str, object] | None = None
    turn_ids: list[int] = []
    try:
        if not reusing_collection:
            for pdf in pdf_paths:
                document = ingest_document(ingestor, elements_repo, collection["id"], pdf)
                ingested_doc_ids.append(document["id"])
                embedded = embed_document_elements(
                    repo=elements_repo,
                    service=embedding_service,
                    collection_id=collection["id"],
                    doc_id=document["id"],
                    batch_size=args.embed_batch_size,
                )
                print(f"Embedded {embedded} elements for doc_id={document['id']}.")
        else:
            print("Skipping ingestion and embedding; existing collection will be used.")

        chat = chats_repo.create_chat(
            collection_id=collection["id"],
            title=f"M4 multi-turn QA flow {datetime.utcnow():%Y-%m-%d %H:%M:%S}",
        )
        print(f"Chat created id={chat['id']} for collection {collection['id']}")

        for turn_idx, question in enumerate(args.questions, start=1):
            print("=" * 80)
            print(f"Running QA turn #{turn_idx} for question: {question}")
            result = run_qa_turn(
                chat_id=chat["id"],
                question=question,
                top_k=args.top_k,
                enable_image_vqa=args.enable_image_vqa,
                enable_memory_summarizer=args.enable_memory_summarizer,
            )
            print_rendered_answer(result.answer_text)
            print_multi_turn_evidences(result.evidences)
            print("=" * 80)
            print(f"Turn #{turn_idx} stored with id={result.turn_id}")
            turn_ids.append(result.turn_id)
    finally:
        if not args.keep:
            print("Cleaning up created chat/collection/documents...")
            if chat:
                chats_repo.delete_chat(chat["id"])
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
                    f"Re-run with --collection-id {collection['id']} to reuse the indexed documents.",
                )
            else:
                print("Keep flag enabled; leaving data in place.")
            if turn_ids:
                print(f"Stored turn ids: {', '.join(str(turn_id) for turn_id in turn_ids)}")


def print_multi_turn_evidences(evidences: list[dict[str, object]]) -> None:
    """Reuse the verbose single-turn evidence logger for clarity in multi-turn runs."""
    print_single_turn_evidences(evidences)


if __name__ == "__main__":
    main()
