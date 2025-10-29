# OBQA Demo Overview

This repository hosts a sequential Paper Question-Answering demo that ties answers back to PDF evidence.

## Module Responsibilities

- **EviQAsys/backend/app/api** – FastAPI routers exposing upload, indexing, and QA endpoints.
- **EviQAsys/backend/app/schemas** – Pydantic models mirroring database tables and HTTP payloads.
- **EviQAsys/backend/app/services** – Synchronous pipeline steps:
  - `preprocess`: normalize MinerU content and repair headers.
  - `index`: create section aggregates and deterministic embeddings.
  - `db_access`: thin helpers for OceanBase reads/writes.
  - `embedding`: adapters for Qwen embedding calls or stubs.
  - `llm`: DsPy orchestrators targeting Alibaba LLMs.
  - `memory`: maintain per-chat state and evidence numbering.
  - `qa_flow`: sequential orchestration combining rewrite → retrieve → answer.
  - `retrieval`: vector + metadata lookups for candidate elements.
  - `integrations`: HTTP/DB clients for MinerU, OceanBase, and DsPy.
- **EviQAsys/backend/app/repositories** – Table-specific CRUD helpers for `collections`, `documents`, `elements`, `chats`, `turns`, and `turn2evidence`.
- **frontend/src** – React pages, components, and API clients that render upload/index/QA flows with evidence highlighting.
- **scripts** – Operational utilities (e.g., seeding data, running demo pipeline).
- **docs/diagrams** – Source files for diagrams referenced in `docs/en`.

## Agent Collaboration

- **Control Agent** orchestrates the overall pipeline inside `services/qa_flow`, coordinating upload, indexing, and question flows.
- **Retrieval Agent** (services/retrieval) focuses on vector + metadata lookups via OceanBase repositories.
- **Memory Agent** (services/memory) maintains evidence numbering continuity and caches prior turn context.
- **Answer Agent** (services/llm + qa_flow) builds multimodal prompts and formats answers with `[Evidence#no]` anchors.

Each agent runs synchronously during request handling; no background workers or asynchronous orchestrators are introduced until later milestones.
