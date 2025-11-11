Here’s the English translation of your milestone-based roadmap:

---

## Serial Phase Division (6 Milestones)

> Each phase defines a **Definition of Done (DoD)** and a **Main Task List** (in execution order).
> Complete the items sequentially in this order.

---

### **M0. Development Environment & Repository Skeleton**

*(Goal: Launch an empty API)*

**DoD:** On local/server, `uvicorn` can launch FastAPI; frontend can send a minimal GET health check.
**Main Tasks:**

1. Create two Conda environments:
   `quest` (for FastAPI + DsPy) and `jzMinerUVllm` (for the local MinerU service).
   Start OceanBase Docker (minimal single-node setup).
2. Organize repository directories (recommended):
   `backend/`, `frontend/`, `dependency/` (link directly to existing examples).
3. Backend: create minimal route group → `GET /healthz → {ok:true}`.
4. Frontend: implement the thinnest possible `fetch` wrapper to call the health check (no state management framework needed).

---

### **M1. Database Initialization & Repository Layer**

*(Goal: Tables available, CRUD testable)*

**DoD:** Six tables created in OceanBase; backend can perform CRUD via repository functions; `GET /api/collections` returns an empty list in the unified envelope.
**Main Tasks:**

1. Write DDL according to the unified data model:

   * Tables: `collections / documents / elements / chats / turns / turn2evidence`
   * Key FKs: `documents.collection_id`, `elements.doc_id`, and bridge table PK `turn2evidence (turn_id, evidence_no)`.
   * Use `ON DELETE CASCADE` on relevant foreign keys; defer optional performance indexes (e.g., `idx_chat_turn`, `idx_turn_element`) to later milestones.

2. Implement **non-ORM** table gateways (repository layer):
   `collections_repo.py`, `documents_repo.py`, `elements_repo.py`, `chats_repo.py`, `turns_repo.py`, `turn2evidence_repo.py`

3. Use the connection example from `dependency/oceanBaseDemo` to validate connection and transaction handling.

---

### **M2. Document Upload → MinerU Parsing → Storage**

*(Goal: First PDF parsed into Elements and stored)*

**DoD:** Frontend uploads one PDF; backend runs synchronously:
calls MinerU → receives `content_list + md_text` → normalizes → writes into `documents/elements`; frontend shows the PDF in “Document List.”
**Main Tasks:**

1. Backend `POST /collections/{id}/documents` (multipart): control service receives file, saves metadata, **blocking call** to MinerU API to obtain `content_list / md_text`.

2. Perform “Header hierarchy repair + unified elementization”:
   For each element, write `header_name / level_nav / page_no / bbox / text_caption`, etc.;
   generate brief section summaries for header nodes; enforce “**element is the minimal index unit**.”

3. Store data under **unified text view**:

   * Plain text: `header_name + level_nav + text_content`
   * Header: `header_name + level_nav + section_summary`
   * Image/Table: use caption as `text_content`, store image as base64 in `image_base64`

4. Use `dependency/minerUparseDemo/parse_pdf_minerU.py` as integration sample.

> Note: Unlike “frontend polling status,” this demo adopts **synchronous storage** for predictability and simplicity — aligned with the blueprint’s “synchronous and deterministic services” principle.

---

### **M3. Embedding & Retrieval**

*(Goal: Retrieve vector candidates successfully)*

**DoD:** Backend script or API triggers embedding for newly stored elements, writing to `elements.vec_embedding`; `/retrieval/test` can return candidate elements with metadata.
**Main Tasks:**

1. Textual elements (text/table/equation): embed `text_content`;
   visual elements (image): embed `image_base64`.
   Use Qwen-series or multimodal embedding models — start from `dependency/multiModalEmbedding` demo, then encapsulate in `embedding_service.py`.
2. Extend repository layer with **simple vector similarity search** (cosine + TopK).
   Retrieval returns `doc_id / page_no / bbox / elem_type`.
3. Reserve interface hooks for “deduplication and type bucketing” (skip complex logic for now).

---

### **M4. QA Backbone (DsPy Orchestration & Evidence Binding)**

*(Goal: Return answers with `[Evidence#no]` anchors)*

**DoD:** Within a collection, user can create a Chat;
`POST /chats/{chat_id}/turns` returns `answer` text containing `[Evidence#1]...[Evidence#n]`;
`turn2evidence` table records mappings;
`GET /turns/{turn_id}/evidences` returns each evidence’s `doc_id/page_no/bbox/snippet`.
**Main Tasks:**

1. **Question Rewriting:** use DsPy/LLM to perform lightweight rewrite for retrieval.
2. **Retrieval:** run vector search with rewritten query, group/filter by type, obtain candidate evidence elements.
3. **Memory:** concatenate last few turns (e.g., 3); summarize older ones.
4. **Answer Generation:** construct multimodal prompt (text + image list) and **explicitly instruct model to output anchors** (`[Evidence#no]`);
   after generation, write `(turn_id, evidence_no → element_id)` into the bridge table to ensure traceability.
5. Use `dependency/DspyDemo` as the base for LLM/orchestration integration.

---

### **M5. Minimal Frontend (Collections / Upload / Chat / Highlight Navigation)**

*(Goal: End-to-end demo is runnable)*

**DoD:** Frontend includes four minimal pages/views:
Collections list, Document page (with upload), Chat page (multi-turn log), and PDF viewer with evidence highlighting.
Clicking `[Evidence#no]` navigates and highlights the source region.
**Main Tasks:**

1. **API Integration:** Implement and connect these minimal endpoints (base path `/api`):

   * `GET /api/collections`, `POST /api/collections`, `DELETE /api/collections/{id}`
   * `POST /api/collections/{id}/documents`, `GET /api/documents/{doc_id}/file`
   * `POST /api/collections/{id}/chats`, `GET /api/chats/{chat_id}`
   * `POST /api/chats/{chat_id}/turns`, `GET /api/turns/{turn_id}/evidences`

2. **Anchor Parsing & Jump:**
   Chat UI renders `[Evidence#no]` as clickable links;
   clicking calls the evidences API, triggers PDF viewer to jump to `page_no` and highlight via `bbox`.

3. **UI Thinness:**
   Implement with pure React + `fetch` wrapper, no global state library;
   adopt unified response envelope.

---

## **Suggested Implementation Order (Codex Agent Task List)**

1. **M0:** Initialize Conda envs and empty FastAPI; verify `GET /healthz`.
2. **M1:** Execute DDL, finish `collections_repo` & `documents_repo`, verify `GET /collections`.
3. **M2:** Integrate MinerU parsing, finish `POST /collections/{id}/documents` with synchronous storage; minimal upload form on frontend.
4. **M3:** Implement `embedding_service`, vectorize stored elements; add `/retrieval/test`.
5. **M4:** Connect DsPy pipeline: rewrite → retrieve → answer (with anchors); store in `turns` & `turn2evidence`.
6. **M5:** Complete chat page + PDF highlight navigation; unify response envelope; build an end-to-end demo script.

---

## **M6. Acceptance Script (End-to-End Self-Test)**

* **Create Collection** → `POST /api/collections {name:"Demo"}` → returns `id`
* **Upload PDF** → returns `doc_id`
* **Vectorize** → trigger batch process
* **Create Chat** → `POST /api/collections/{id}/chats`
* **Ask Question** → `POST /api/chats/{chat_id}/turns` → answer includes `[Evidence#1]`
* **Click Anchor** → frontend calls `GET /api/turns/{turn_id}/evidences` → PDF viewer navigates and highlights

Each step aligns with the system’s **Requirements**, **Data Model**, **Blueprint**, and **Interaction Design**.
