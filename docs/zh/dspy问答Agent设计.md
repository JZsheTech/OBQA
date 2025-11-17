# **《多模态论文问答 Agent 模块设计文档（与现有架构对齐版）》**

（定性描述 · 无代码细节 · 含伪代码形式流程图）

本页是 **M4“问答主干”** 的补充说明文档，重点描述「问答 Agent」在当前 PaperQA 系统中的职责边界与落地模块映射，需与以下文档保持一致：

- `docs/zh/多模态论文问答系统设计文档.md`
- `docs/zh/数据模型.md`
- `docs/zh/开发路线图.md`

---

# 1. **整体工作流概述（结合现有接口）**

入口为 API：

- `POST /api/chats/{chat_id}/turns`（规划中，尚未在代码中落地）：创建一个新的问答轮次；
- 数据表：`collections / documents / elements / chats / turns / turn2element`（见《数据模型》）。

当用户在某个 Collection 下的 Chat 中提问时，系统基于：

- 当前 `chat_id` 的历史轮次（`turns`）；
- 该 Chat 所属 Collection 下的 `documents/elements`；
- 已向量化的元素（`elements.vec_embedding`）；
- 可选的图像元素 `image_base64`（通过视觉问答集成）；

进行检索、推理，最终返回一个带有 `[Evidence#no]` 锚点的回答文本，并在后端以 `[Elem#<element_id>]` 的形式持久化证据引用（写入 `turn2element` 桥表）。

从模块职责上，问答 Agent 仍然划分为两大类组件：

### **A. DSPy 模块（纯“文本↔文本”的智能决策）**

用于：

* 对话记忆摘要（Memory Service，M4）
* 检索判别（是否需要 RAG、需要哪些 elem_type）
* 问句重写（为向量检索生成适配 query）
* 图像子问题生成（仅生成文本子问题，不直接携带图片）
* 最终回答合成（基于文本上下文与 `[Elem#id]` 锚点）

> 约束（与路线图一致）：`dspy.Signature` 内不携带任何图片字段，只接受 `element_id / elem_type / text_content` 等文本信息。

### **B. 普通 Python 服务（工程类任务）**

用于：

* 读写数据库（`chats / turns / turn2element / elements`）
* 调用 MinerU 完成 PDF 解析（`services/integrations/MinerUAdapter`）
* 调用向量服务完成向量化与向量检索（`services/embedding.EmbeddingService` + `services/retrieval.Retriever`）
* 调用视觉问答接口进行图像理解（待补充：`services/integrations/vision_vqa.py`）
* 保存 `turn` 到 `element` 的映射（仓储层 + `services/mapping/evidence_mapper.py`）
* 构造上下文（caption、附近文本、历史聊天摘要）

顶层控制流将以 `services/qa_flow` 下的 orchestrator 为主（例如 `run_qa_turn()`），对外通过 FastAPI 路由暴露为 `/api/chats/{chat_id}/turns`。

---

# 2. **系统模块总览（与当前目录结构对齐）**

结合《系统设计文档》的架构蓝图，问答 Agent 所在位置可以简化为：

```
                ┌────────────────────────┐
                │        前端 React       │
                └────────────┬───────────┘
                             │  POST /api/chats/{chat_id}/turns
                             ▼
                ┌────────────────────────┐
                │   API Router (/api)    │
                │   - turns 路由(规划中) │
                └────────────┬───────────┘
                             ▼
                ┌────────────────────────┐
                │ Control / QA Flow     │
                │ services/qa_flow      │
                └────────────┬───────────┘
                             ▼
        ┌────────────────────────────────────────────────┐
        │                问答 Agent 内部                 │
        │                                                │
        │  ┌──────────────────────────────────────────┐  │
        │  │  Memory + DSPy Programs (文本编排)       │  │
        │  └──────────────────────────────────────────┘  │
        │  ┌──────────────────────────────────────────┐  │
        │  │  Retrieval Service                       │  │
        │  │  - services/retrieval.Retriever         │  │
        │  │  - services/embedding.EmbeddingService  │  │
        │  └──────────────────────────────────────────┘  │
        │  ┌──────────────────────────────────────────┐  │
        │  │  Answer Service                          │  │
        │  │  - DSPy 回答生成                         │  │
        │  │  - services/mapping.evidence_mapper      │  │
        │  └──────────────────────────────────────────┘  │
        └────────────────────────────────────────────────┘
                             │
                             ▼
                ┌────────────────────────┐
                │ OceanBase Repositories │
                │ collections/documents  │
                │ elements/chats/turns   │
                │ turn2element           │
                └────────────────────────┘
```

其中：

- **解析/入库**：由 `services/ingestion/DocumentIngestor` 和 `services/integrations/MinerUAdapter` 在 M2 完成；
- **向量检索**：由 `services/retrieval.Retriever` 在 M3 完成，对外有测试接口 `GET /api/retrieval/test`；
- **问答 Agent**：在 M4 基于上述能力串联，并新增 DSPy 编排、记忆、证据锚点映射。

---

# 3. **各模块说明（定性描述 + 对应代码模块）**

## **3.1 历史对话加载（Python，Memory Service 输入）**

职责：为当前问题构造「历史对话文本」输入，作为 Memory DSPy 模块的输入之一。

数据来源：

* 表：`chats`（获取 `collection_id`、`max_turn_order` 等元信息）
* 表：`turns`（读取当前 `chat_id` 下的历史问答，按 `order` 排序）

逻辑要点：

* 支持策略：
  * **全量历史**：读取该 Chat 全部 `turns`；
  * **最近 N 轮**：按 `order` 倒序截取最近 N 轮，避免上下文过长。
* 将历史问答串联为统一文本 `history_text`，供 Memory DSPy 使用（如 `"User: ...\nAssistant: ..."`）。

实现位置（规划）：

* `services/qa_flow/history_loader.py`（待创建）或 `services/memory` 下的辅助函数；
* 底层依赖 `...repositories.TurnsRepository` 和 `ChatsRepository`。

> 说明：这一步是纯 DB 访问和字符串拼接，不涉及 DSPy。

---

## **3.2 记忆摘要模块（DSPy，Memory Service）**

职责：对 `history_text` 做压缩，总结出对后续问答有用的对话记忆 `memory_summary`。

输入：

* `history_text`: 从 3.1 生成；

输出：

* `memory_summary`: 对话的压缩表示，可控制字数/Token 上限。

伪代码形式：

```python
memory_summary = Summarizer(history_text)
```

设计要点：

* Memory 策略可以被 DSPy 调优，但输出需保持为可序列化的文本字段；
* 后续模块（检索判别、问句重写、回答生成）均可携带 `memory_summary` 作为附加输入；
* 不直接访问数据库或元素，只消费 3.1 的文本结果。

实现位置（规划）：

* `services/memory/` + `services/llm/` 中的 DSPy Program。

---

## **3.3 检索判别模块（DSPy，是否走 RAG）**

职责：根据当前问题与记忆摘要，判断本轮是否需要访问 `elements` 做 RAG 检索，同时决定需要哪些元素类型。

输入：

* `question: str`
* `memory_summary: str`

输出：

* `need_retrieve: bool`
* `elem_types: list[str]`（例如：`["text","header","image"]`）

伪逻辑：

```python
need_retrieve, elem_types = RetrievalDecider(question, memory_summary)
```

使用场景：

* `need_retrieve = False`：直接走「纯对话问答」，不访问向量检索，仅基于记忆与指令回答；
* `need_retrieve = True`：进入 3.4 问句重写 + 3.5 元素检索。

实现位置（规划）：

* 作为一个 DSPy Program，位于 `services/llm/` 或 `services/qa_flow` 中。

---

## **3.4 问句重写模块（DSPy，输入 Retrieval Service）**

职责：将用户原始问题 + 记忆摘要重写为适合向量检索的 query 文本。

输入：

* `question`
* `memory_summary`

输出：

* `search_query: str`（用于向量检索或全文检索）

伪逻辑：

```python
search_query = QueryRewriter(question, memory_summary)
```

设计要点：

* `search_query` 将被传入 `Retriever.retrieve_topk()` 中的 `query_text`；
* 可以利用 DSPy 的自动提示词/结构化模板机制提升检索精度；
* 不负责具体的 TopK / 向量运算。

实现位置（规划）：

* DSPy Program，归属 `services/llm` 或 `services/qa_flow`。

---

## **3.5 元素检索（Python，Retrieval Service）**

职责：基于重写后的 query，从 `elements` 表检索候选元素，提供统一的文本上下文（含类型与位置信息）。

对应实现：

* `services/retrieval/retriever.py` 中的 `Retriever` 类；
* 使用 `services/embedding.EmbeddingService` 计算向量；
* 访问 `ElementsRepository` 完成向量 TopK 或全文检索。

关键方法（已存在）：

```python
results = retriever.retrieve_topk(
    collection_id=collection_id,
    query_text=search_query,
    top_k=top_k,
    doc_id=doc_id,
    elem_types=elem_types,
    search_mode="vector",  # 或 "fulltext"
)
```

返回结构（`RetrievalResult`）包含：

* `element_id / doc_id / collection_id`
* `page_no / bbox / elem_type`
* `score`
* `text_content`（统一文本视图，已在 M2 入库时构造）

说明：

* 这里只做「候选召回」与简单的类型过滤；
* 不负责 Evidence 去重与 `[Elem#id]` 锚点生成（交给 Answer/DSPy）。

---

## **3.6 图像子问题生成（DSPy，可选图像理解路径的文本部分）**

职责：对于检索结果中 `elem_type == "image"` 的元素，基于当前问题与上下文生成一个适合发送给视觉问答接口的「文本子问题」。

输入：

* `question`
* `memory_summary`
* `local_context`：由 Python 侧拼接而成，通常包括：
  * 图片 caption（`text_caption`）
  * 图片所在章节/邻近元素文本（通过 `level_nav` 和 `order` 范围获取）
  * 当前检索到的其他文本 Evidence 片段

输出：

* `image_question: str`

伪逻辑：

```python
image_question = ImageQuestionGenerator(
    question=question,
    memory_summary=memory_summary,
    local_context=image_local_context,
)
```

重要约束：

* DSPy 模块仅处理文本，不直接携带 `image_base64`；
* `image_question` 将被传给 Python 集成模块（视觉问答）。

---

## **3.7 调用视觉问答接口（Python，VLM 集成）**

职责：从数据库取回指定 image 元素的 `image_base64`，调用 OpenAI 兼容的视觉问答接口，拿到该图片的「文字摘要」。

输入：

* `element_id: int`
* `image_question: str`

输出：

* `image_note: str`（对图片的纯文本理解/摘要）

建议函数原型（与《系统设计文档》保持一致）：

```python
def vision_vqa_summarize(element_id: int, derived_question: str) -> str:
    """从 DB 读取 image_base64，调用视觉问答接口（OpenAI 兼容），返回文字摘要。"""
```

实现位置（规划）：

* `services/integrations/vision_vqa.py`（待实现）
* 读取 `elements.image_base64`；调用外部 VLM；返回摘要字符串。

说明：

* 视觉问答全程在 Python 集成层完成，不进入 DSPy；
* 返回的 `image_note` 将被拼接回文本上下文，供 3.8 回答生成使用。

---

## **3.8 最终回答生成模块（DSPy，Answer Service）**

职责：融合用户问题、记忆摘要、文本 Evidence 与图像摘要文本，生成带 `[Elem#<element_id>]` 锚点的回答文本。

输入：

* `question`
* `memory_summary`
* `text_evidences: list[EvidenceText]`
  * 每个元素至少包含：`element_id / elem_type / text_content`
* `image_evidences: list[EvidenceText]`
  * 来自 3.7 的 `image_note` 与 caption 拼接后的文本，附带 `element_id`

输出：

* `answer_text: str`（自然语言答案，内部使用 `[Elem#<element_id>]` 形式的锚点）

伪逻辑：

```python
answer_text = AnswerComposer(
    question=question,
    memory_summary=memory_summary,
    text_evidences=text_evidences,
    image_evidences=image_evidences,
)
```

设计要点：

* LLM 输出中的证据引用统一采用 `[Elem#<element_id>]` 形式（如 `[Elem#123]`）；
* DSPy Program 需要在 prompt 中明确约束「引用元素时必须带 `[Elem#id]` 标签」；
* 不直接关心 `evidence_no`，只负责 `element_id`。

---

## **3.9 持久化与 Evidence 映射（Python）**

职责：将本轮问答写入 `turns` 表，并将本轮使用到的元素写入 `turn2element`；同时按 chat 维度构建 `element_id → evidence_no` 的映射，并把回答文本中的 `[Elem#id]` 替换为 `[Evidence#no]`，并将`[Evidence#no]`对应的文档名、page_idx和bbox信息一起返回给前端, 方便高亮展示。

涉及表：

* `turns`
* `turn2element`（主键 `(chat_id, turn_id, element_id)`）

涉及模块：

* `...repositories.TurnsRepository / Turn2ElementRepository / ElementsRepository`
* `services/mapping/evidence_mapper.py`

核心逻辑拆分为三步：

1. **写入 Turns 与 Turn2Element**

   * 创建一条新的 `turn` 记录（包含 `user_question`、`llm_answer_text`、`used_llm_model` 等）；
   * 从 `answer_text` 中解析出所有 `[Elem#id]`，或直接使用检索结果中的 `element_id` 集合作为本轮引用集合；
   * 对于每个 `element_id`，插入一条 `turn2element` 记录（`chat_id, turn_id, element_id, turn_order`）。

2. **按 Chat 维度构建 element_id → evidence_no 映射**

   * 收集当前 Chat 下所有历史 `answer_text` 中的 `[Elem#id]` 出现顺序；
   * 使用 `services/mapping/evidence_mapper.build_evidence_no_mapping()` 生成映射：

     ```python
     mapping = build_evidence_no_mapping(history_element_ids)
     ```

3. **替换回答中的 `[Elem#id]` 为 `[Evidence#no]`**

   * 对当前轮的 `answer_text` 调用：

     ```python
     final_answer = replace_elem_tags_with_evidence(answer_text, mapping)
     ```

   * 只在 API 输出中使用 `[Evidence#no]`，数据库中仍保存原始的 `[Elem#id]`。

> 说明：`evidence_no` 不入库存储，而是每次在返回前按「元素在该 chat 中的首次出现顺序」动态计算，满足《开发路线图》中 M4 的约束。

---

# 4. **整体控制流（伪代码，结合现有服务）**

下面是与当前架构对齐的顶层 pipeline 伪代码，逻辑会最终落地在 `services/qa_flow` 中，并通过 `POST /api/chats/{chat_id}/turns` 暴露。

```python
def run_qa_turn(collection_id: int, chat_id: int, question: str) -> dict:
    # 1. 载入历史对话（Python）
    history_text = load_history_text(chat_id)  # 调用仓储层，拼接为文本

    # 2. 记忆摘要（DSPy）
    memory = Summarizer(history_text)

    # 3. 判别是否需要检索（DSPy）
    need_retrieve, elem_types = RetrievalDecider(question, memory)

    text_evidences: list[EvidenceText] = []
    image_evidences: list[EvidenceText] = []

    if need_retrieve:
        # 4. 重写检索问句（DSPy）
        search_query = QueryRewriter(question, memory)

        # 5. 调用 Retrieval Service（Python）
        retriever = Retriever()
        candidates = retriever.retrieve_topk(
            collection_id=collection_id,
            query_text=search_query,
            top_k=TOP_K,
            elem_types=elem_types,
        )

        # 6. 拆分文本/图像候选，构造文本 Evidence
        text_evidences = build_text_evidences_from_candidates(candidates)
        image_candidates = [c for c in candidates if c["elem_type"] == "image"]

        # 7. 可选：对每张图片走图像理解路径
        for img in image_candidates:
            local_ctx = build_image_local_context(img, text_evidences, question)
            img_q = ImageQuestionGenerator(question, memory, local_ctx)  # DSPy
            img_note = vision_vqa_summarize(img["element_id"], img_q)    # Python 集成
            image_evidences.append(
                EvidenceText(
                    element_id=img["element_id"],
                    text_content=img["text_content"] + "\n" + img_note,
                    elem_type="image",
                )
            )

    # 8. 最终回答生成（DSPy）
    answer_text = AnswerComposer(
        question=question,
        memory_summary=memory,
        text_evidences=text_evidences,
        image_evidences=image_evidences,
    )

    # 9. 持久化记录（Python）
    turn_id = save_turn_and_elements(
        chat_id=chat_id,
        question=question,
        raw_answer_text=answer_text,  # 内部携带 [Elem#id]
        used_evidence_element_ids=collect_element_ids(text_evidences, image_evidences),
    )

    # 10. 构建 evidence_no 映射并替换标签
    history_element_ids = collect_all_element_ids_from_chat(chat_id)
    mapping = build_evidence_no_mapping(history_element_ids)
    final_answer = replace_elem_tags_with_evidence(answer_text, mapping)

    return {
        "turn_id": turn_id,
        "answer": final_answer,  # 文本中带 [Evidence#no]
        # anchors 可选：前端可用来高亮 PDF
    }
```

> 该伪代码只展示模块交互顺序，具体函数/类名在实现时以 `services/qa_flow` 和 `schemas` 中的实际定义为准。

---

# 5. **模块边界总结（最重要的三句话）**

## **（1）所有“文本 → 文本”的智能判断、重写、决策、合成 → DSPy 模块。**

包括：

* 对话记忆摘要（Memory）
* 是否检索（RetrievalDecider）
* 问句重写（QueryRewriter）
* 给图片造子问题（ImageQuestionGenerator）
* 最终回答生成（AnswerComposer，输出 `[Elem#id]`）

## **（2）所有涉及 I/O、DB、向量检索、VLM 接口 → 普通 Python 服务。**

包括：

* 加载历史对话（`load_history_text`）
* 调用 MinerU 解析 PDF（`DocumentIngestor + MinerUAdapter`）
* 调用向量服务与 `Retriever.retrieve_topk`
* 构造 local context、拆分文本/图像候选
* 调用视觉问答接口 `vision_vqa_summarize`
* 写入 `turns / turn2element` 并构建 `evidence_no` 映射

## **（3）DSPy 只消费 Python 的结果，不与图片或数据库直接交互。**

* DSPy 侧签名只接受纯文本字段（含 `element_id` 等标识）；
* 图像内容必须先在 Python 侧通过视觉问答转成文本后再回注；
* Evidence 展示编号由 Python 侧（`evidence_mapper` + 仓储层）动态生成与替换。

---

# 6. **可以直接交给 coder 的话**

> 「这个文档就是问答 Agent 的模块交互说明。实现时按以下原则：
> 1）在 `services/qa_flow` 中实现顶层 orchestrator，并通过 `/api/chats/{chat_id}/turns` 对外暴露；
> 2）所有 LLM/DSPy 逻辑（记忆、判别、重写、回答、图像子问题）都封装为只收/返文本的 Program，统一使用 `[Elem#id]` 做证据锚点；
> 3）所有 DB 访问、向量检索、视觉问答、`turn2element` 写入与 `[Evidence#no]` 映射全部用 Python 服务完成；
> 4）API 层只看见 `[Evidence#no]` 和锚点列表，内部存储始终以 `element_id` 为主键，满足《数据模型》与《开发路线图》的约束。」

