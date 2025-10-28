# Development Road Map

**Guiding principles**
- Keep the pipeline sequential: upload → parse → store → retrieve → answer → highlight.
- Favor the documented stack (FastAPI, DsPy, MinerU demo service, OceanBase) with minimal abstractions.
- Target demo-ready functionality first; defer optimizations, concurrency, and automation.

## Milestone 0 · Environment Baseline (0.5 day)
- Confirm working access to MinerU (`dependency/minerUparseDemo/parse_pdf_minerU.py`) and OceanBase demo scripts; capture example payloads for later stubs.
- Create a lightweight `.env.sample` covering OceanBase DSN, MinerU endpoint, LLM keys; document activation steps for `quest` and `jzMinerUVllm` Conda envs.
- Prepare seed data: at least one sample PDF and an empty OceanBase schema cloned from `Data_Model.md`.
- Deliverable: README snippet describing how to start supporting services and verify connections.

## Milestone 1 · Architecture Blueprint & Directory Layout (0.5 day)
- Draft a high-level component diagram covering MinerU parsing service, FastAPI backend modules (ingest, retrieval, QA), OceanBase storage, and React client; emphasize sequential flow and data handoffs.
- Define the repository directory scaffold under `EviQAsys/` (e.g., `backend/app/{api,services,repositories,schemas}`, `frontend/src/{pages,components,api}`, `scripts/`, `docs/diagrams/`); ensure names stay simple and match teaching goals.
- Add placeholder `README` sections describing module responsibilities and how agents interact (Control/Retrieval/Memory/Answer).
- Deliverable: Architecture sketch saved under `docs/en/` (markdown or diagram export) plus committed directory stubs with `.gitkeep` where needed.

## Milestone 2 · Interface & Data Contracts (1.5 days)
- Define FastAPI Pydantic models reflecting the global schema (`collections`, `documents`, `elements`, `chats`, `turns`, `turn2evidence`) plus DTOs for upload, retrieval, and chat requests.
- Draft OpenAPI routes (no logic yet) for: collection CRUD, document upload, indexing trigger, chat start, turn submit, evidence lookup. Ensure responses expose `[Evidence#no]`, `bbox`, and `page_no`.
- Establish simple MinerU and OceanBase client adapters: sequential wrapper functions with typed request/response payloads based on captured samples.
- Capture interface assumptions in `docs/en/service_interface_use.md` notes or inline comments (e.g., synchronous blocking calls, basic error formats).
- Deliverable: FastAPI skeleton with routes, schemas, and contract docstrings checked in; mock unit tests asserting schema serialization.

## Milestone 3 · Backend Implementation & Self-Testing (3 days)
- Implement sequential pipeline services:
  1. `upload_document`: save file, call MinerU parse service synchronously, persist document metadata.
  2. `index_elements`: transform MinerU `content_list` into unified element structure, generate section summaries, request embeddings (stub with deterministic vectors for now), write to OceanBase via simple repository functions.
  3. `qa_turn`: rewrite query (DsPy wrapper), perform sequential retrieval against OceanBase (text first, optional image/table follow-up), build prompt, call LLM, store turn/evidence links.
- Keep orchestration linear; use blocking calls and explicit `try/except` logging rather than background jobs.
- Add self-tests:
  - CLI or pytest script that runs the full pipeline against the seed PDF with mocked external calls (MinerU, embeddings, LLM).
  - In-memory validation ensuring evidence numbering continuity and Turn2Evidence integrity.
- Deliverable: Backend runs locally via `uvicorn`, all self-tests pass, and sample JSON transcripts (question → answer + evidence) stored under `sample_data/backend/`.

## Milestone 4 · Frontend Integration (2 days)
- Scaffold a minimal React single-page app (Vite + TypeScript optional) served statically; use fetch + plain hooks, no state managers.
- Implement flows:
  - Collection & document management: forms for creating collections, uploading PDFs, viewing status.
  - QA workspace: chat panel showing turn history, answer text with clickable `[Evidence#no]`, evidence list panel displaying section metadata, page number, and thumbnail if available.
  - Document viewer: iframe or canvas overlay that highlights bounding boxes based on `bbox` and `page_no`; rely on sequential loading rather than virtualization.
- Wire to backend endpoints; handle loading/error states with simple banners.
- Smoke-test end-to-end by performing upload → index → question in the browser using the seed PDF.
- Deliverable: Frontend served locally, minimal CSS, demonstration script recorded or documented outlining the full workflow.

## Milestone 5 · Demo Polish & Handover (0.5 day)
- Write a concise demo script plus troubleshooting FAQ highlighting the sequential pipeline and evidence traceability.
- Capture environment startup scripts (e.g., shell snippets to launch MinerU FastAPI, OceanBase Docker, backend, frontend).
- Optional stretch if time remains: replace embedding/LLM stubs with actual services, ensuring graceful fallback if unavailable.
- Deliverable: Updated `README` with demo instructions, checklist confirming all milestones verified.
