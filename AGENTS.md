# OBQA Development Guidelines

These instructions apply to the entire repository. They distill the English documentation under `docs/en/` into concise guidance for a single developer working with AI assistance.

---

## Mission Overview
- Build a demo Paper Question-Answering system that produces answers *with explicit evidence anchors* tied back to PDF elements.【docs/en/Requirement_Document.md】
- Follow the sequential pipeline: **upload → parse → store → retrieve → answer → highlight**. Avoid premature optimization or asynchronous complexity; keep control flow simple and inspectable.【docs/en/Develop_Road_Map.md】【docs/en/Design_Document.md】

## Recommended Toolchain
- **Backend**: Python FastAPI running inside the `quest` Conda environment. Write services and adapters as thin, synchronous wrappers around external dependencies.【docs/en/Tech_Stack.md】【docs/en/Develop_Road_Map.md】
- **Frontend**: React (Vite optional) running in the browser; implement minimal state management with idiomatic hooks.
- **Storage**: OceanBase (Docker). Interact through repository modules that map directly to the global schema tables described below.
- **Document Parsing**: MinerU demo FastAPI (`dependency/minerUparseDemo/parse_pdf_minerU.py`). Treat its responses as the source of truth for `content_list` and `md_text`.
- **LLM & Agents**: DsPy orchestrating Alibaba LLMs for query rewriting, retrieval decisions, and multimodal answering. Keep orchestration linear (Control → Retrieval → Memory → Answer agents).【docs/en/Design_Document.md】
- **Embeddings**: Qwen series multimodal embeddings; if unavailable, stub deterministic vectors but keep the interface intact.

## Repository Expectations
- Keep the project root flat with sibling directories like `EviQAsys/`, `docs/`, and `dependency/`. Do **not** place `docs/en/` under the application package.
- Place application code under `EviQAsys/` using a clear scaffold:
  - `backend/app/{api,schemas,services,repositories}` for FastAPI routes, Pydantic models, orchestration logic, and storage access.
    - Within `services/`, break functionality into subpackages such as `preprocess`, `index`, `db_access`, `llm`, `embedding`, and `qa_flow` (or similar) so each pipeline stage has an obvious home.
    - Keep shared connectors (OceanBase clients, MinerU adapters, DsPy orchestrators) under `services/integrations/` or the corresponding repository module.
  - `frontend/src/{pages,components,api}` for UI, API clients, and evidence-highlighting widgets.
  - `scripts/` for ad-hoc utilities (seed database, run pipeline samples).
  - `docs/en/` for living architecture assets (update or extend as milestones evolve).
- Use `.gitkeep` files when you must commit empty directories (per Road Map Milestone 1).【docs/en/Develop_Road_Map.md】
- Database Access: Keep repository modules lightweight—no ORM layer is needed. Use sqlalchemy.text() for direct SQL execution and map results manually to Pydantic models.

## Data & Contracts
- Adopt the unified global schema: `collections`, `documents`, `elements`, `chats`, `turns`, and `turn2evidence`. Keep foreign keys and indexes aligned with the specification and favor straightforward CRUD repositories.【docs/en/Data_Model.md】
- For MinerU ingestion, ensure each Element carries `section_name`, `level_nav`, `text_content`, optional captions, `image_base64`, `bbox_json`, and `page_no`. Maintain the standardized multimodal fields even when stubbing data.【docs/en/Design_Document.md】
- Maintain evidence numbering continuity via the `(chat_id, turn_id, evidence_no)` triplet stored in `turn2evidence`.
- Document every external interface contract (MinerU, OceanBase, DsPy) either in code docstrings or `docs/en/service_interface_use.md`.

## Development Workflow
1. **Environment Baseline**: The runtime stack (MinerU, OceanBase, DsPy, Conda env) is complex and usually provisioned on the developer's workstation. As the AI assistant, concentrate on code and automation scripts—write reproducible setup/test commands and share them with the developer instead of attempting remote deployment. Review `docs/test/` to understand which areas already have validated coverage before requesting new runs. Conceptually verify the demo scripts under `dependency/`, document assumptions, and capture sample payloads plus connection steps in `.env.sample` and README snippets.【docs/en/Develop_Road_Map.md】【docs/en/dependency_tool_service.md】
2. **Architecture Setup**: Maintain updated diagrams/notes under `docs/en/` summarizing module interactions (Control, Retrieval, Memory, Answer agents and their data handoffs).【docs/en/Design_Document.md】
3. **Interface First**: Define Pydantic schemas and FastAPI routes before implementation. Keep request/response models aligned with the data model and QA pipeline (include `[Evidence#no]`, `bbox`, `page_no`).
4. **Sequential Services**: Implement upload, indexing, and QA services as direct synchronous flows. Use explicit logging and `try/except` around external calls; avoid background jobs until the basic demo is solid.
5. **Testing**: Provide CLI or pytest utilities that exercise the full pipeline against sample PDFs with mocked external services. Validate evidence numbering and stored metadata.
6. **Frontend Integration**: Build a minimal but complete flow—collection/document management, QA chat, evidence list, PDF highlight overlay. Use descriptive components and keep state localized.
7. **Demo Polish**: Document startup scripts for MinerU, OceanBase, backend, and frontend. Produce a short demo walkthrough and troubleshooting FAQ once end-to-end flows succeed.

## Coding & Collaboration Notes
- Prefer descriptive module and function names that mirror the pipeline steps (e.g., `upload_document`, `index_elements`, `qa_turn`).
- Keep configuration centralized (environment variables loaded once, injected into services).
- Use type hints, Pydantic models, and dataclasses where appropriate for clarity and AI-assist compatibility.
- Store sample transcripts, payloads, or fixtures under `sample_data/` to aid rapid regression checks.
- Before large changes, update relevant docs to keep design, data model, and roadmap synchronized with reality.

---

Refer back to the English documentation for detailed requirements, but treat this file as the actionable playbook for fast, AI-assisted iteration.
