# usage : python EviQAsys/backend/tests/manual/test_m2_ingest.py 
# 运行前清理之前的多余数据: python EviQAsys/backend/tests/manual/test_m2_ingest.py --reset-db --clear-uploads

# • 增补了一套清理工具，跑手动测试前就能一键清空数据库和上传目录，避免前几次失败留下的垃圾数据。

#   - 在 EviQAsys/backend/app/repositories/maintenance.py:1-47 新增 clear_tables() 与 clear_upload_storage()：按先子表后父表的顺序执行
#     DELETE，并提供对 /tmp/obqa_uploads（或自定义 UPLOAD_DIR）的递归清理+可选重建。模块通过 repositories.__init__ 暴露，方便其他脚本直接调
#     用（EviQAsys/backend/app/repositories/__init__.py:1-24）。
#   - EviQAsys/backend/tests/manual/test_m2_ingest.py:15-110 增加 --reset-db 和 --clear-uploads 参数；在正式写入前若开启这些开关，会调用上
#     述清理函数并打印提示，这样每次手动验证都从干净状态起步。其余流程保持不变，仍然会自动建集合、写入样本 PDF、输出元素统计，并在 --keep
#     未开启时回滚样本数据。

#   验证提示：当前环境里我未重新运行脚本；你可以执行
#   python EviQAsys/backend/tests/manual/test_m2_ingest.py --reset-db --clear-uploads
#   来先清空表和 /tmp/obqa_uploads，随后再进行 MinerU ingest。


from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
from pathlib import Path

PROJECT_ROOT_DIR = Path(__file__).resolve().parents[4]
import sys
sys.path.append(str(PROJECT_ROOT_DIR))


from EviQAsys.backend.app.env_setting import get_oceanbase_settings
from EviQAsys.backend.app.repositories import (
    CollectionsRepository,
    DocumentsRepository,
    ElementsRepository,
    clear_tables,
    clear_upload_storage,
    initialize_database,
)
from EviQAsys.backend.app.services.ingestion.document_ingestor import DocumentIngestor, DuplicateDocumentError

DEFAULT_PDF = Path(__file__).resolve().parents[4] / "sample_data" / "pdf_doc" / "1-Cui et al. - 2019 - Class-Balanced Loss Based on Effective Number of Samples.pdf"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manual MinerU ingestion smoke test.")

    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF, help="Path to a real PDF file for ingestion.")
    parser.add_argument("--keep", action="store_true", help="Keep the ingested rows instead of cleaning up.")
    parser.add_argument("--reset-db", action="store_true", help="Delete all rows from ingestion tables before running.")
    parser.add_argument("--clear-uploads", action="store_true", help="Empty UPLOAD_DIR before running.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    initialize_database()
    if args.reset_db:
        print("Clearing database tables before ingestion...")
        clear_tables()
    if args.clear_uploads:
        cleared = clear_upload_storage()
        print(f"Cleared upload directory: {cleared}")
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
