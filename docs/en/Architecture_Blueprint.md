# Architecture Blueprint

This blueprint captures the minimal sequential flow required for the Paper Question-Answering demo. It focuses on a single path from PDF upload to highlighted answers, avoiding background workers or redundant services.

## High-Level Interaction Diagram

```mermaid
graph TD
    subgraph Client
        A[React Frontend]
    end
    subgraph Backend
        B1[API Router]
        B2[Control Service]
        B3[Retrieval Service]
        B4[Memory Service]
        B5[Answer Service]
    end
    subgraph External
        C1[MinerU Parsing API]
        C2[OceanBase Storage]
        C3[DsPy + Alibaba LLMs]
    end

    A -->|Upload PDF| B1 -->|forward file| B2
    B2 -->|parse request| C1 -->|content_list + md_text| B2
    B2 -->|persist documents & elements| C2
    A -->|Ask question| B1 --> B2
    B2 -->|rewrite query| C3
    B2 -->|retrieve candidates| B3 -->|vector + metadata lookup| C2
    B3 -->|dedupe & cache| B4 -->|evidence context| B5
    B5 -->|multimodal prompt| C3 -->|answer with [Evidence#no]| B5
    B5 -->|store turn & evidence links| C2
    B5 -->|response| B1 -->|answer + anchors| A
```

## Component Responsibilities

| Layer | Components | Responsibilities |
| --- | --- | --- |
| **Frontend** | React pages & components | Provide upload, indexing progress, and chat UI with evidence highlighting. All requests go directly to the FastAPI backend using thin `fetch` wrappers. |
| **Backend API** | `api` routers + Pydantic `schemas` | Define HTTP entry points for upload, indexing trigger, and QA turns. Marshal requests into synchronous service calls and serialize responses with `[Evidence#no]`, `bbox`, and `page_no`. |
| **Services** | `preprocess`, `index`, `db_access`, `embedding`, `retrieval`, `memory`, `llm`, `qa_flow`, `integrations` | Each module owns one pipeline step. Functions are synchronous and composable, orchestrated in `qa_flow`. `integrations` wraps MinerU, OceanBase clients, and DsPy flows without extra abstraction layers. |
| **Repositories** | OceanBase table gateways | Provide direct CRUD helpers for `collections`, `documents`, `elements`, `chats`, `turns`, `turn2evidence`. No ORM required; keep SQL explicit and simple. |
| **External Systems** | MinerU, OceanBase, DsPy/LLMs | Operate as authoritative services. The backend treats them as blocking calls with explicit error handling and retries when needed. |

## Data & Control Flow Summary

1. **Upload** – The frontend uploads a PDF. The backend control service stores metadata, calls MinerU, normalizes the returned `content_list`, and persists documents/elements in OceanBase using repository helpers.
2. **Index** – `index` services generate deterministic embeddings (Qwen or stubs), attach section metadata, and write unified element records. All work occurs within the request scope.
3. **Question** – The control service rewrites the question via DsPy, the retrieval service performs vector and metadata lookups in OceanBase, and the memory service ensures evidence numbering continuity.
4. **Answer** – The answer service builds a multimodal prompt, calls the Alibaba LLM through DsPy, stores the new turn plus evidence links, and returns the answer with `[Evidence#no]` anchors. The frontend resolves anchors to highlight PDF regions using the stored `bbox` and `page_no`.

This structure keeps the architecture intentionally small: a single FastAPI application coordinating deterministic modules with predictable side effects. No background queues or event buses are introduced until the core demo flow is complete.
