

# 🧩 Data Model Design Specification

> The system adopts a **unified global schema** instead of creating separate `documents` or `elements` tables for different `collections`.
> All documents, elements, and conversation data are maintained within the same logical space to facilitate **cross-paper retrieval** and **unified index management**.

---

## I. Base Tables

### **1. collections**

| Field         | Type        | Description                    |
| ------------- | ----------- | ------------------------------ |
| `id`          | BIGINT (PK) | Primary key, auto-increment ID |
| `name`        | VARCHAR     | Collection name                |
| `created_at`  | DATETIME    | Creation time (DEFAULT CURRENT_TIMESTAMP) |
| `description` | VARCHAR     | Collection description         |

**Constraints:**

* `PRIMARY KEY (id)`

---

### **2. documents**

| Field           | Type        | Description                                       |
| --------------- | ----------- | ------------------------------------------------- |
| `id`            | BIGINT (PK) | Primary key, auto-increment ID                    |
| `collection_id` | BIGINT (FK) | Belonging collection                              |
| `title`         | VARCHAR     | Paper title                                       |
| `md_text`       | TEXT        | Markdown full text returned by MinerU             |
| `file_name`     | VARCHAR     | Original filename                                 |
| `file_path`     | VARCHAR     | Absolute path of the persisted PDF                |
| `file_sha256`   | VARCHAR     | SHA-256 hash of the uploaded PDF for dedup checks |
| `file_size_bytes` | BIGINT    | Binary size of the upload in bytes                |
| `num_pages`     | INT         | Number of pages                                   |
| `element_count` | INT         | Number of parsed elements in doc                  |
| `created_at`    | DATETIME    | Creation time (DEFAULT CURRENT_TIMESTAMP)         |

**Constraints:**

* `PRIMARY KEY (id)`
* `FOREIGN KEY (collection_id)` → `collections(id)` ON DELETE CASCADE

---

### **3. elements**

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | BIGINT (PK) | Primary key, auto-increment ID |
| `doc_id` | BIGINT (FK) | Associated document ID |
| `order` | INT | Reading order parsed from the content_list, starting from 0 |
| `elem_type` | VARCHAR | Element type (`text`/`header`/`image`/`table`/`equation`); enforce via CHECK constraint |
| `header_name` | VARCHAR | Chapter/section title (e.g., 1.1.1 message passing), excluding parent titles. |
| `header_level` | INT | Header level (only for elements of type 'header') |
| `level_nav` | VARCHAR | Hierarchical navigation path (e.g., 1. introduction > 1.1 GNN > 1.1.1 message passing) |
| `text_content` | TEXT | Text content |
| `text_caption` | TEXT | Caption/annotation for images or tables |
| `image_base64` | TEXT | Image content (Base64 encoded) |
| `bbox_json` | JSON | Element's position information in the PDF; a list of 4 integers representing the bounding box |
| `page_no` | INT | Page number |
| `vec_embedding` | VECTOR | Vector embedding (for similarity search); dimension configurable via `VECTOR_DIM` env var |
| `order_start` | VARCHAR | The starting element ID of the section corresponding to a Header element |
| `order_end` | VARCHAR | The ending element ID of the section corresponding to a Header element |
| | | |


**Constraints:**

* `PRIMARY KEY (id)`
* `FOREIGN KEY (doc_id)` → `documents(id)` ON DELETE CASCADE

---

### **4. chats**

| Field             | Type        | Description                         |
| ----------------- | ----------- | ----------------------------------- |
| `id`              | BIGINT (PK) | Primary key, auto-increment ID      |
| `collection_id`   | BIGINT (FK) | Belonging collection                |
| `created_at`      | DATETIME    | Chat creation time (DEFAULT CURRENT_TIMESTAMP) |
| `title`           | VARCHAR     | Chat title                          |
| `max_evidence_no` | BIGINT      | Maximum evidence number in the chat, start from 1 |
| `max_turn_order` | BIGINT      | the numer of turns in the chat, start from 1 |

**Constraints:**

* `PRIMARY KEY (id)`
* `FOREIGN KEY (collection_id)` → `collections(id)` ON DELETE CASCADE

---

### **5. turns**

| Field              | Type        | Description                              |
| ------------------ | ----------- | ---------------------------------------- |
| `id`               | BIGINT (PK) | Primary key, auto-increment ID           |
| `chat_id`          | BIGINT (FK) | Belonging chat                           |
| `order`            | INT         | The turn’s order within the chat         |
| `user_question`    | TEXT        | User question                            |
| `llm_answer_text`  | MEDIUMTEXT  | LLM answer                               |
| `llm_thought_text` | MEDIUMTEXT  | LLM reasoning process (chain of thought) |
| `created_at`       | DATETIME    | Creation time (DEFAULT CURRENT_TIMESTAMP) |
| `response_tokens`  | INT         | Token consumption for this turn          |
| `used_llm_model`   | VARCHAR     | LLM model identifier (e.g., gpt-4o-mini) |

**Constraints:**

* `PRIMARY KEY (id)`
* `FOREIGN KEY (chat_id)` → `chats(id)` ON DELETE CASCADE

---

## II. Bridge Table

This table records the **evidence elements** referenced in each conversation turn.
In this design, **Evidence is not a standalone entity** — it is implicitly represented by the triplet `(chat_id, turn_id, evidence_no)`.
Each `turn` directly binds its evidences to specific `element_id` entries, with `turn_order` helping to restore the recent dialogue context.

---

### **Turn2Evidence**

| Field         | Type        | Description                                                                        |
| ------------- | ----------- | ---------------------------------------------------------------------------------- |
| `chat_id`     | BIGINT (FK) | Belonging chat ID (`chats.id`)                                                     |
| `turn_id`     | BIGINT (FK) | Belonging turn ID (`turns.id`)                                                     |
| `turn_order`  | INT         | The turn’s order within the chat (redundant field for quick context recovery)      |
| `evidence_no` | INT         | Evidence index starting from 1 in each turn (e.g., `[Evidence#1]`, `[Evidence#2]`) |
| `element_id`  | BIGINT (FK) | Linked element ID (`elements.id`)                                                  |
| `created_at`  | DATETIME    | Record creation time (DEFAULT CURRENT_TIMESTAMP)                                   |

**Constraints:**

* `PRIMARY KEY (turn_id, evidence_no)` → ensures unique evidence numbering per turn
* `FOREIGN KEY (chat_id)` → `chats(id)` ON DELETE CASCADE
* `FOREIGN KEY (turn_id)` → `turns(id)` ON DELETE CASCADE
* `FOREIGN KEY (element_id)` → `elements(id)` ON DELETE CASCADE

Performance indexes (e.g., on `(chat_id, turn_order)` or `(turn_id, element_id)`) are deferred to later milestones and intentionally omitted in M1.

---

## III. Structural Highlights

* All tables share a **global schema**, with `collection_id` used to distinguish datasets.
* The `elements` table serves as the **core indexing layer**, supporting multimodal retrieval (text + image + table).
* The `turn2evidence` table dynamically binds **Turn ↔ Evidence ↔ Element**, enabling traceable evidence linkage.
* `evidence_no` **increments independently within each chat**, starting from 1.

Timestamp convention: tables include `created_at` with `DEFAULT CURRENT_TIMESTAMP`; no `updated_at` fields in M1.
