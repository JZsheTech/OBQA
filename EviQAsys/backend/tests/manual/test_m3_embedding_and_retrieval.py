from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import time

PROJECT_ROOT = Path(__file__).resolve().parents[4]
import sys

sys.path.append(str(PROJECT_ROOT))

from EviQAsys.backend.app.repositories import ElementsRepository, initialize_database  # noqa: E402
from EviQAsys.backend.app.services.embedding import EmbeddingService  # noqa: E402
from EviQAsys.backend.app.services.retrieval import Retriever  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manual M3 validation: embed missing elements and run retrieval checks.",
    )
    parser.add_argument("--collection-id", type=int, required=True, help="Target collection id.")
    parser.add_argument("--doc-id", type=int, default=None, help="Optional document scope.")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="Number of elements to embed per batch.",
    )
    parser.add_argument(
        "--max-to-embed",
        type=int,
        default=0,
        help="Optional cap for embedding operations (0 = no cap).",
    )
    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help="Query text used for retrieval smoke test.",
    )
    parser.add_argument("--top-k", type=int, default=5, help="TopK for retrieval.")
    parser.add_argument(
        "--search-mode",
        choices=["vector", "fulltext"],
        default="vector",
        help="Retrieval mode.",
    )
    parser.add_argument(
        "--elem-types",
        type=str,
        default=None,
        help="Comma separated element types filter.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    initialize_database()
    elements_repo = ElementsRepository()
    embedding_service = EmbeddingService()
    retriever = Retriever(embedding_service=embedding_service, elements_repo=elements_repo)

    total_embedded = embed_missing_elements(
        repo=elements_repo,
        service=embedding_service,
        collection_id=args.collection_id,
        doc_id=args.doc_id,
        batch_size=args.batch_size,
        max_to_embed=args.max_to_embed,
    )
    print(f"[{datetime.utcnow()}] Embedded {total_embedded} new elements.")

    if not args.query:
        print("No query provided; skipping retrieval test.")
        return

    elem_types = parse_elem_types(args.elem_types)
    print(
        f"[{datetime.utcnow()}] Running retrieval: collection={args.collection_id}, "
        f"doc_id={args.doc_id}, mode={args.search_mode}, top_k={args.top_k}",
    )
    start = time.perf_counter()
    results = retriever.retrieve_topk(
        collection_id=args.collection_id,
        query_text=args.query,
        top_k=args.top_k,
        doc_id=args.doc_id,
        elem_types=elem_types,
        search_mode=args.search_mode,
    )
    duration_ms = (time.perf_counter() - start) * 1000
    print(f"Retrieval completed in {duration_ms:.1f} ms; returned {len(results)} candidates.")
    if not results:
        print("No candidates returned.")
        return
    for idx, item in enumerate(results, start=1):
        bbox_display = item.get("bbox")
        print(
            f"{idx}. element_id={item['element_id']} doc_id={item['doc_id']} "
            f"type={item['elem_type']} page={item.get('page_no')} score={item['score']:.4f} "
            f"bbox={bbox_display}",
        )
        preview = (item.get("text_content") or "").strip()
        if preview:
            print(f"   text: {preview[:200]}")


def embed_missing_elements(
    *,
    repo: ElementsRepository,
    service: EmbeddingService,
    collection_id: int,
    doc_id: int | None,
    batch_size: int,
    max_to_embed: int,
) -> int:
    total_embedded = 0
    max_to_embed = max(0, max_to_embed)
    batch_size = max(1, batch_size)
    while True:
        remaining = repo.list_unembedded(
            collection_id=collection_id,
            doc_id=doc_id,
            limit=batch_size,
        )
        if not remaining:
            break
        payload = service.batch_embed_elements(remaining)
        repo.update_embeddings(payload)
        total_embedded += len(payload)
        sample_elem = next(iter(payload.keys()))
        sample_dim = len(next(iter(payload.values())))
        print(
            f"[{datetime.utcnow()}] Embedded batch of {len(payload)} "
            f"(sample element id={sample_elem}, dim={sample_dim})",
        )
        if max_to_embed and total_embedded >= max_to_embed:
            break
    return total_embedded


def parse_elem_types(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    values = [entry.strip() for entry in raw.split(",") if entry.strip()]
    return values or None


if __name__ == "__main__":
    main()
