
---

# 📘 PaperQA System Design Document

## 1. System Module Design

**Note:** `Evidence#no` refers to the *evidence number*.

| Module                           | Design Description                                                                                                                                                                                                                                                     |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Evidence Generation Strategy** | During the Answer generation phase, the LLM automatically outputs text containing `[Evidence#no]` anchors. Each anchor corresponds to a pre-indexed **Element** (including `bbox` coordinates), enabling front-end highlight and positioning.                          |
| **Indexed Element Structure**    | Each object parsed by MinerU from the `content_list` is treated as an **Element**, serving as the minimal indexing unit. An Element can be text, image, table, or equation, supporting unified multimodal indexing and retrieval.                                       |
| **Answer–Evidence Binding**      | The Answer embeds Markdown anchors `[Evidence#no]`; clicking an anchor in the front-end navigates to and highlights the corresponding content.                                                                                                                         |
| **Highlight System**             | Based on MinerU’s coordinate (`bbox`) information, the front-end renders visual highlights, enabling source-level traceability within the original document.                                                                                                           |
| **System Architecture**          | The system is composed of four cooperative core agents: **Control Agent**, **Retrieval Agent**, **Memory Agent**, and **Answer Agent**. OceanBase serves as the unified storage layer for both index data and vector embeddings, ensuring scalability and consistency. |

---

## 2. Detailed Design: Pipeline Workflow

### 🧩 P1. Document Upload and Indexing

1. **Parsing Phase**

   * MinerU parses the uploaded PDF to obtain a `content_list` (containing both text and images) and the full text in Markdown format (`md_text`).

2. **Document Storage**

   * The full text (`md_text`) is stored in the `Documents` table, linked to its corresponding `Collection`, from which both `collection_id` and `doc_id` are obtained.

3. **Header Hierarchy Repair**

   * The `preprocess_header()` function scans and repairs the document’s hierarchical heading structure (based on title patterns such as `1`, `1.1`, `2.1.2`, etc.), adding for each Element:

     * `section_name`: the nearest parent heading title
     * `level_nav`: the complete hierarchical navigation path

4. **Section Aggregation and Summary Generation**

   * Text between a given heading and the next heading at the same level is concatenated sequentially.
   * A lightweight summarization model generates a summary for each section, which is stored in the corresponding header node.

5. **Unified Element Structure**

   * To standardize retrieval, every Element must contain both `text_content` and `image_content` fields:

     | Type          | `text_content` Construction                        | `image_content`   |
     | ------------- | -------------------------------------------------- | ----------------- |
     | **pure_text** | `section_name + level_nav + text_content`          | —                 |
     | **header**    | `section_name + level_nav + section_summary`       | —                 |
     | **image**     | `section_name + level_nav + image_caption`         | base64 image data |
     | **table**     | `section_name + level_nav + table_caption`         | base64 image data |
     | **equation**  | `section_name + level_nav + equation_text (LaTeX)` | base64 image data |

6. **Vectorization and Storage**

   * Unified multimodal embeddings are generated using the **Qwen** series embedding models:

     * **Textual types** (Text, Table, Equation): embeddings are generated from `text_content` only (Table/Equation types do not use image modality).
     * **Image type**: embeddings are generated from `image_content`.
   * The embeddings, along with metadata (`collection_id`, `doc_id`, etc.), are stored in the `Elements` table within OceanBase.

---

### 💬 P2. Question-Answering Process

7. **Question Input and Rewriting**

   * The user selects a target `Collection` and submits a question.
   * An Alibaba LLM performs **query rewriting** to produce a more retrieval-friendly version of the question.

8. **Vector Retrieval and Evidence Generation**

   * The rewritten query is used to perform vector search in the `Elements` table.
   * Retrieved Elements are grouped by type (header, text, table, equation, image) and passed to the **AnswerAgent**, which filters relevant evidences.
     Useful evidences are kept and deduplicated against previously used ones under the same `chat_id`, continuing sequential numbering (e.g., `[Evidence#3]`, `[Evidence#4]`, etc.).
   * The mapping between `turn_id`, `chat_id`, `evidence_no`, and `element_id` is stored in the `Turn2Evidence` table.

9. **Answer Generation and Binding**

   * **Prompt Construction**:

     * **Text modality**: concatenate multiple `text_content` blocks with delimiters, each labeled with its Evidence number.
     * **Image modality**: include corresponding base64 images in an `images` list and explicitly describe the mapping between each image index and its Evidence number in the prompt.
   * The Alibaba multimodal **VLM model** (text + image input) generates an Answer containing embedded `[Evidence#no]` anchors.

10. **Front-End Interaction**

* The front-end parses `[Evidence#no]` anchors from the Answer, locates the corresponding Element using its `doc_id`, `bbox`, and `page_no`, and highlights the original content — achieving synchronized visualization between **Answer** and **Evidence**.

---
