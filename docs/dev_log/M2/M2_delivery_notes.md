# M2 Delivery Notes

This milestone wires together the synchronous ingestion loop described in `M2_plan.md`.

## Backend

- Added MinerU HTTP adapter with configurable endpoint + timeout, plus header repair, TF-IDF summarizer, and element unifier modules.
- `DocumentIngestor` coordinates upload persistence, dedup (`collection_id + file_name + file_sha256`), MinerU parsing, normalization, and transactional writes to `documents`/`elements`.
- `documents` schema now stores `md_text`, `file_sha256`, `file_size_bytes`, and `element_count`; repositories expose batch insert helpers.
- Upload API: `POST /api/collections/{id}/documents` validates PDFs, surfaces 409 on duplicates, and returns `{doc_id, file_name, file_size_bytes, status}`.
- Listing API: `GET /api/collections/{id}/documents` returns `parse_status`, element counts, timestamps, and file sizes for the frontend list.
- Manual test script: `EviQAsys/backend/tests/manual/test_m2_ingest.py --collection-id <id> --pdf <path>` ingests real PDFs from `sample_data/pdf_doc`, prints element statistics, and cleans up rows by default.

## Frontend

- Minimal “Document Console” view (React) with collection selector, upload form, and table showing `{name/size/created/element_count/parse_status}`.
- API client now targets `/api/collections/{id}/documents` for both upload and listing; status messages surface backend errors directly.

## Configuration

- Environment knobs added in `env_setting.py`: `UPLOAD_DIR`, `MAX_UPLOAD_MB`, `MINERU_MODE`, `MINERU_ENDPOINT`, `MINERU_TIMEOUT_S`, and `BATCH_SIZE`.
- Default upload root lives outside the repo (`/tmp/obqa_uploads`) to avoid polluting tracked folders.
