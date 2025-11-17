# OBQA Demo Overview

This repository hosts a sequential Paper Question-Answering demo that ties answers back to PDF evidence.

## Module Responsibilities

- **EviQAsys/backend/app/api** – FastAPI routers exposing upload, indexing, and QA endpoints.
- **EviQAsys/backend/app/schemas** – Pydantic models mirroring database tables and HTTP payloads.
- **EviQAsys/backend/app/services** – Synchronous pipeline steps:
  - `preprocess`: normalize MinerU content and repair headers.
  - `index`: create section aggregates and deterministic embeddings.
  - `db_access`: thin helpers for OceanBase reads/writes.
  - `embedding`: adapters for Jina_embedding_v4 embedding calls or stubs.
  - `llm`: DsPy orchestrators targeting Alibaba LLMs.
  - `memory`: maintain per-chat state and evidence numbering.
  - `qa_flow`: sequential orchestration combining rewrite → retrieve → answer.
  - `retrieval`: vector + metadata lookups for candidate elements.
  - `integrations`: HTTP/DB clients for MinerU, OceanBase, and DsPy.
- **EviQAsys/backend/app/repositories** – Table-specific CRUD helpers for `collections`, `documents`, `elements`, `chats`, `turns`, and `turn2element`.
- **frontend/src** – React pages, components, and API clients that render upload/index/QA flows with evidence highlighting.
- **scripts** – Operational utilities (e.g., seeding data, running demo pipeline).
- **docs/diagrams** – Source files for diagrams referenced in `docs/en`.

## Agent Collaboration

- **Control Agent** orchestrates the overall pipeline inside `services/qa_flow`, coordinating upload, indexing, and question flows.
- **Retrieval Agent** (services/retrieval) focuses on vector + metadata lookups via OceanBase repositories.
- **Memory Agent** (services/memory) caches prior turn context.
- **Answer Agent** (services/llm + qa_flow) cites anchors as `[Elem#<element_id>]`; the API layer later maps these to display `[Evidence#no]` per-chat.

Each agent runs synchronously during request handling; no background workers or asynchronous orchestrators are introduced until later milestones.

## project structure


```
.
├── debug
├── dependency
│   ├── api_key
│   ├── DspyDemo
│   ├── minerUparseDemo
│   ├── multiModalEmbedding
│   └── oceanBaseDemo
├── docs
│   ├── diagrams
│   ├── en
│   └── zh
├── EviQAsys
│   ├── backend
│   │   └── app
│   │       ├── api
│   │       ├── repositories
│   │       ├── schemas
│   │       └── services
│   │           ├── db_access
│   │           ├── embedding
│   │           ├── index
│   │           ├── integrations
│   │           ├── llm
│   │           ├── memory
│   │           ├── preprocess
│   │           ├── qa_flow
│   │           └── retrieval
│   └── frontend
│       └── src
│           ├── api
│           ├── components
│           └── pages
├── log -> /data2/jproject/mylogging/log
├── sample_data -> /data/QUEST/jzshe/project/OBpaperQA/sample_data
└── scripts
```

## Embedding & Retrieval Configuration

- Set `VECTOR_DIM` to the dimensionality returned by the embedding model (default: `2048` for `jinaembeddingv4`).
- Configure the embedding adapter via environment variables (default values shown):
  - `EMBEDDING_ENDPOINT=http://localhost:7701/v1/embeddings`
  - `EMBEDDING_MODEL=jinaembeddingv4`
  - `EMBEDDING_TIMEOUT_S=60`
  - `EMBEDDING_MAX_RETRIES=1`
  - `EMBEDDING_API_KEY` / `EMBEDDING_API_KEY_HEADER` (optional, for hosted gateways).
- Trigger manual validation with:

```bash
conda activate quest
python EviQAsys/backend/tests/manual/test_m3_embedding_and_retrieval.py \
  --collection-id 1 \
  --query "graph neural network pretraining" \
  --top-k 5
```

The script embeds any `elements.vec_embedding IS NULL` rows, records the effective vector dimension, and prints TopK retrieval samples via `/services/retrieval`.

## Database Maintenance

- Reset schema (drop all tables and recreate):

```
conda activate quest
python scripts/reset_database.py --yes
```
