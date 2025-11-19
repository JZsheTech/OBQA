# M4 问答主干阶段执行计划（DSPy 文本编排与 Evidence 锚点）

> 规划依据：
>
> - 《开发路线图.md》中的 **M4. 问答主干（DSPy 文本编排、证据锚点绑定）**
> - 《工程细节/dspy问答Agent设计.md》
> - 《工程细节/Evidence渲染规范.md》

---

## 0. 应当参考的接口
不要擅自写一个openai兼容的LLM调用接口，用原始的方式去调用LLM，应该参考我提供的示例代码：

### LLM调用
项目中的：dependency/chatLLM
dependency/chatLLM/multimodal_qwen25_vl_72b_ollama.py 是图片理解LLM的调用方式
dependency/chatLLM/text_llama3_70b_ollama.py 是文本理解LLM的调用方式，注意我们一般要用的是dspy形式的调用。

### 数据库查询
充分复用M2和M3阶段EviQAsys/backend/app 中已经实现的数据库相关接口，遇到不够的再手动添加。

## 1. 阶段目标与 DoD 复述

### 1.1 阶段目标（从用户视角）

在某个 Collection 下新建 Chat 后，前端调用：

- `POST /api/chats/{chat_id}/turns` 发送用户问题；
- 后端走一整套 **DSPy 文本编排 + 检索 + 可选图像理解** 流程；
- 返回结果中：
  - `answer_text` 文本内部使用若干个 `[Elem#<element_id>]` 锚点；
  - 同时返回 `evidences` 列表，每一项包含 `element_id / evidence_no / document_id / page_index / bbox / elem_type / snippet` 等字段；
  - 前端根据 `answer_text` 与 `evidences` 将 `[Elem#id]` 渲染为 `[Evidence#no]`，并能联动 PDF 高亮。

### 1.2 DoD（与路线图一致）

- 在某 Collection 下创建 Chat；
- 调用 `POST /api/chats/{chat_id}/turns`：
  - `answer_text` 中含有合法格式的 `[Elem#<element_id>]` 锚点；
  - API 响应附带 `evidences` 数组，元素至少包含：
    - `element_id`
    - `evidence_no`
    - `document_id`
    - `page_index`
    - `bbox`
    - `elem_type`
    - `snippet`（或等价的简要文本展示字段）；
  - `turn2element` 表写入 `(chat_id, turn_id, element_id)` 映射，**仅**覆盖答案文本中真实出现的 `[Elem#id]`；
  - `answer_text` 自身不发生字符串替换，数据库和 API 内均保持 `[Elem#id]` 形式；
- 对于同一 `chat_id`：
  - `element_id → evidence_no` 映射在一轮响应内稳定；
  - evidence 编号按「该 Chat 中元素首次被引用顺序」生成，符合《Evidence 渲染规范》；
- 至少完成一套端到端人工验证流程（M0–M3 已完成的前提下）：
  - 上传真实 PDF → MinerU 解析入库；
  - 元素完成向量化；
  - 提问并获得带 Evidence 的回答；
  - 前端（或手工）依据 `evidences` 能定位到 PDF 中的对应区域。

---

## 2. 前置依赖与边界条件

在进入 M4 实现前，需要满足：

1. **数据侧依赖（来自 M1–M3）：**
   - OceanBase 中已存在并可用的表：
     - `collections / documents / elements / chats / turns / turn2element`；
   - `elements` 表中：
     - 已有标准化字段 `elem_type / page_no / bbox / text_content / text_caption / image_base64 / level_nav` 等；
     - 对于至少一个 Demo Collection，已通过 M2 流程完成 MinerU 解析与元素入库；
   - 向量化与检索侧：
     - `elements.vec_embedding` 已被 M3 批量填充；
     - `services/embedding/embedding_service.py`、`services/retrieval/retriever.py` 可用；
     - `/api/retrieval/test` 通过人工验证可以返回 TopK 候选元素。

2. **工程目录结构要求：**
   - `EviQAsys/backend/app/` 中已经存在：
     - `api/`（路由分组）
     - `repositories/`（仓储层）
     - `schemas/`（Pydantic 模型）
     - `services/qa_flow/`（问答流程 orchestrator，若不存在需在 M4 中新建）
     - `services/retrieval/`、`services/embedding/` 等；
   - M4 新增模块需遵循：
     - DSPy 相关 Program 位于 `services/llm/` 或 `services/qa_flow/`；
     - Evidence 相关映射逻辑位于 `services/mapping/`；
     - 视觉问答集成位于 `services/integrations/vision_vqa.py`。

3. **DSPy 与 LLM 环境：**
   - `quest` Conda 环境中已安装 DSPy 及底层 LLM 客户端；
   - 模型调用统一走后端已有的 LLM 封装（若尚未落地，可在 M4 同步补齐最小封装）；
   - 遵守约束：`dspy.Signature` 内 **不携带图片字段**，只接受纯文本与标识符（`element_id / elem_type / text_content` 等）。

4. **规范约束（必须遵守）：**
   - LLM / DSPy 输出中的证据锚点统一为 `[Elem#<element_id>]`；
   - `turns.answer_text` 始终存储 `[Elem#id]`，不写入 `evidence_no`；
   - `evidence_no` 仅在 API 响应中临时生成，**不入库**；
   - 前端所有 Evidence 渲染与 PDF 高亮逻辑基于 `element_id` 和 `evidences` 列表完成。

---

## 3. M4 工作包拆分与顺序

M4 建议拆分为 5 个互相依赖的工作包，按顺序推进：

1. **包 A：API 与外围 Schema 打通（最小跑通 skeleton）**
2. **包 B：历史对话加载与记忆摘要（Memory Service）**
3. **包 C：检索决策、问句重写与候选 Evidence 构造**
4. **包 D：Answer 生成 + Evidence 映射与持久化**
5. **包 E：可选图像理解路径与配置开关**

每个工作包都建议在完成后进行一次独立的静态检查，然后再进入下一包。

---

## 4. 包 A：API 与外围 Schema 打通

### 4.1 新增 / 调整后端路由

在 `api` 层新增或完善：

- `POST /api/chats/{chat_id}/turns`

设计要点：

- 请求体（示例）：
  - `question: str`
  - 可选字段：`collection_id`（若未从 chat 关联中推导）、`top_k`、`enable_image_vqa` 等；
- 响应体遵循统一 envelope：

  ```jsonc
  {
    "code": "OK",
    "data": {
      "turn_id": 123,
      "chat_id": 3,
      "answer_text": ".... [Elem#456] ....",
      "evidences": [
        {
          "element_id": 456,
          "evidence_no": 1,
          "document_id": 5,
          "page_index": 10,
          "bbox": [100, 120, 250, 300],
          "elem_type": "text",
          "snippet": "..."
        }
      ]
    }
  }
  ```

- 错误情况（如找不到 chat / collection、向量服务不可用）返回统一错误码；
- 路由层只负责参数校验、当前用户/collection 权限检查（若有）、调用 `qa_flow.run_qa_turn()`。

### 4.2 schemas 设计

在 `schemas` 目录中新建或扩展：

- `TurnCreateRequest`：
  - `question: str`
  - 可选：`top_k: int | None`、`enable_image_vqa: bool | None`；
- `EvidenceItem`：
  - `element_id: int`
  - `evidence_no: int`
  - `document_id: int`
  - `page_index: int`
  - `bbox: list[float] | None`
  - `elem_type: str`
  - `snippet: str | None`
  - 可选：`title: str | None`；
- `TurnResponse`：
  - `turn_id: int`
  - `chat_id: int`
  - `answer_text: str`
  - `evidences: list[EvidenceItem]`

实现注意：

- schemas 命名与字段需与《Evidence 渲染规范》保持一致；
- 预留字段（如 `title`）即使前期不填充，也应在 Schema 中设计好，后续可渐进增强。

### 4.3 qa_flow Orchestrator 壳体

在 `services/qa_flow` 下新增（如不存在）：

- `qa_orchestrator.py`（命名可根据现有约定微调）：

  ```python
  def run_qa_turn(collection_id: int, chat_id: int, question: str, *, top_k: int = 10, enable_image_vqa: bool = False) -> dict:
      """顶层控制函数，后续各阶段逐步填充内部逻辑。"""
  ```

实现步骤：

1. 包 A 阶段仅实现「空跑通」：
   - 从仓储层读取 Chat / Collection 基本信息（校验存在性）；
   - 暂时用占位实现返回固定 `answer_text` 和空 `evidences`；
   - 保证整条 API 调用链（路由 → orchestrator → schemas → 统一 envelope）正常工作；
2. 后续包 B–E 在此函数内部逐步填充真实逻辑。

验收点：

- 手工调用 `POST /api/chats/{chat_id}/turns` 能获得 `code=OK` 的固定占位响应；
- 错误 chat_id / collection_id 时能获得明确错误码。

---

## 5. 包 B：历史对话加载与记忆摘要（Memory Service）

对应《dspy问答Agent设计.md》的 3.1 与 3.2。

### 5.1 历史对话文本加载

在 `services/qa_flow` 或单独 `services/memory/` 下实现：

- 函数示例：`load_history_text(chat_id: int) -> str`

行为：

- 调用 `ChatsRepository` / `TurnsRepository` 读取该 `chat_id` 下历史轮次；
- 按时间顺序拼接为单个 `history_text` 字符串，形如：

  ```text
  [User] Q1...
  [Assistant] A1...
  [User] Q2...
  [Assistant] A2...
  ```

- 控制最大长度（例如按字符数或 Token 数截断，保留最近若干轮），避免提示词过长；
- 历史文本中若包含 `[Elem#id]`，按原样保留，不做替换。

仓储层要求：

- 若尚未有 `TurnsRepository` / `ChatsRepository`，在 M4 中最小补齐：
  - 查询接口：`list_turns_by_chat(chat_id)`；
  - 字段至少包含：`id / question / answer_text / created_at`。

### 5.2 记忆摘要 DSPy Program

在 `services/llm/` 或 `services/memory/` 中实现：

- Program 示例：`MemorySummarizer`：

  ```python
  def summarize_history(history_text: str) -> str:
      """调用 DSPy/LLM，对 history_text 做压缩，返回 memory_summary。"""
  ```

设计要点：

- 输入：`history_text: str`
- 输出：`memory_summary: str`，长度适中，可配置最大字数；
- 策略：
  - 可以是简单摘要（列出主要主题、结论）；
  - 保留对后续检索有帮助的信息（如之前已经讨论过的关键术语、实验设置等）；
- 落地形式：
  - 初期可直接通过现有 LLM 封装实现（不需要一次到位做完整 DSPy Program 调优）；
  - 保留 Program 封装，以便后续替换为更复杂的 DSPy pipeline。

### 5.3 qa_flow 中集成

在 `run_qa_turn` 中补齐：

1. 调用 `load_history_text(chat_id)`；
2. 调用 `summarize_history(history_text)` 获得 `memory_summary`；
3. 将 `memory_summary` 作为后续检索判别与回答生成的输入之一。

验收点：

- 对于有历史对话的 Chat，`history_text` 打印可见；
- `memory_summary` 内容合理且长度受控；
- 失败时（例如没有历史对话），能够退化到使用空字符串或简单占位摘要。

---

## 6. 包 C：检索决策、问句重写与候选 Evidence 构造

对应《dspy问答Agent设计.md》的 3.3–3.5。

### 6.1 检索判别 DSPy Program

在 `services/llm/` 中实现：

- Program 示例：`RetrievalDecider`：

  ```python
  def decide_retrieval(question: str, memory_summary: str) -> tuple[bool, list[str]]:
      """返回 need_retrieve, elem_types。"""
  ```

行为：

- 输入：
  - `question: str`
  - `memory_summary: str`
- 输出：
  - `need_retrieve: bool`：是否需要访问 `elements`；
  - `elem_types: list[str]`：需要关注的元素类型（如 `["text", "header", "image"]`）。

策略建议：

- 针对非常开放或摘要型问题，倾向于开启检索；
- 对于「继续刚才的回答」类问题，可根据 `memory_summary` 决定是否仅用记忆回答。

### 6.2 问句重写 DSPy Program

在 `services/llm/` 或 `services/qa_flow/` 中实现：

- Program 示例：`QueryRewriter`：

  ```python
  def rewrite_query(question: str, memory_summary: str) -> str:
      """生成适合向量检索的 search_query。"""
  ```

策略：

- 将用户问题转化为短句 / 关键短语；
- 合理引入上下文关键词（来自 `memory_summary`）。

### 6.3 调用 Retrieval Service

在 `run_qa_turn` 中增加：

1. 若 `need_retrieve` 为 `False`：
   - 跳过检索，后续 AnswerComposer 仅基于 `question + memory_summary` 回答；
2. 若 `need_retrieve` 为 `True`：
   - 调用 `QueryRewriter` 得到 `search_query`；
   - 使用现有 `Retriever`：

     ```python
     candidates = retriever.retrieve_topk(
         collection_id=collection_id,
         query_text=search_query,
         top_k=top_k,
         elem_types=elem_types,
         search_mode="vector",
     )
     ```

   - 返回的 `candidates` 应包含：
     - `element_id / doc_id / collection_id`
     - `page_no / bbox / elem_type`
     - `score`
     - `text_content`（统一文本视图）

### 6.4 文本 Evidence 构造与初步过滤

基于 `candidates` 构造：

- `text_evidences: list[EvidenceText]`

其中 `EvidenceText` 至少包含：

- `element_id: int`
- `elem_type: str`
- `text_content: str`

处理逻辑：

- 将 `elem_type` 为 `text` / `header` / `table` / `equation` / `image` 的元素统一纳入；
- 对 `image` 及多模态元素：
  - 先仅使用 caption 作为 `text_content`；
  - 图像理解后的 `image_note` 将在包 E 中补充。

可选优化：

- 对得分较低的候选做 TopK 截断；
- 对同一元素的重复召回做去重（同一 `element_id`）。

验收点：

- 在日志中可以看到：
  - `need_retrieve` 判定结果；
  - `search_query` 文本；
  - 返回的候选 `element_id` 列表及其 `text_content` 片段。

---

## 7. 包 D：Answer 生成 + Evidence 映射与持久化

对应《dspy问答Agent设计.md》的 3.8–3.9 以及《Evidence渲染规范.md》。

### 7.1 Answer 生成 DSPy Program

在 `services/llm/` 中实现：

- Program 示例：`AnswerComposer`：

  ```python
  def compose_answer(
      question: str,
      memory_summary: str,
      text_evidences: list[EvidenceText],
      image_evidences: list[EvidenceText],
  ) -> str:
      """生成带 [Elem#<element_id>] 锚点的 answer_text。"""
  ```

关键约束：

- 输出中的证据引用必须是 `[Elem#<element_id>]` 格式；
- Prompt 中明确要求：
  - **引用证据时必须带锚点**；
  - 锚点中的 `element_id` 必须来自 `text_evidences / image_evidences` 提供的 ID；
  - 不得自行虚构不存在的 `element_id`；
- 不负责 `evidence_no`。

### 7.2 解析 `[Elem#id]` 并写入 turns / turn2element

在 `services/mapping/evidence_mapper.py` 中实现：

1. **锚点解析：**

   - 函数：`extract_element_ids_from_answer(answer_text: str) -> list[int]`
   - 逻辑：
     - 使用正则匹配所有 `[Elem#(\d+)]`；
     - 按出现顺序返回 `element_id` 列表；
     - 在单个turn内，每个element只统计1次；

2. **写入 Turns：**

   - 调用 `TurnsRepository.create_turn(...)`：
     - 存储 `chat_id / question / answer_text / created_at` 等；
     - `answer_text` 原样带 `[Elem#id]`。

3. **写入 Turn2Element：**

   - 仅对答案文本中真实出现的 `element_id` 写 `turn2element` 记录；
   - 主键 `(chat_id, turn_id, element_id)`；
   - 忽略未在 answer 中显式引用但参与上下文的候选元素；
   - 若同一 `element_id` 多次出现在 `answer_text` 中，仅写入一条映射记录。

### 7.3 Chat 级 element_id → evidence_no 映射

在 `services/mapping/evidence_mapper.py` 中实现：

1. **收集历史元素 ID：**

   - 函数示例：`collect_all_element_ids_from_chat(chat_id: int) -> list[int]`
   - 基于 `TurnsRepository`，依 turn.order 升序遍历所有 `answer_text`；
   - 使用 `extract_element_ids_from_answer` 收集每个 turn 中出现的 `element_id` 序列；
   - 拼接成一个大列表，如 `[123, 45, 8, 123, 999, ...]`；

2. **生成 mapping：**

   - 函数：`build_evidence_no_mapping(history_element_ids: list[int]) -> dict[int, int]`
   - 遍历列表，按首次出现顺序为每个 `element_id` 分配递增的 `evidence_no`（从 1 开始）；
   - 返回 `element_id → evidence_no` 字典；

3. **当前响应需要的 evidences：**

   - 在 `run_qa_turn` 中，获取本轮使用到的 `used_element_ids`（来自 text/image evidences）；
   - 调用 `ElementsRepository` 查询这些元素的：
     - `document_id / page_no / bbox / elem_type / snippet / title` 等；
   - 根据 mapping 生成 `evidences` 列表：

     ```python
     evidences = [
         {
             "element_id": elem.id,
             "evidence_no": mapping[elem.id],
             "document_id": elem.document_id,
             "page_index": elem.page_no,
             "bbox": elem.bbox,
             "elem_type": elem.elem_type,
             "snippet": elem.text_content[:N],  # 简要片段
         }
         for elem in ...
     ]
     ```

### 7.4 qa_flow 最终组装与返回

在 `run_qa_turn` 中最终实现：

1. 调用 AnswerComposer 得到 `answer_text`；
2. 写 turn 与 turn2element；
3. 从历史中构建 `element_id → evidence_no` 映射；
4. 组装 `evidences` 列表；
5. 返回：

   ```python
   return {
       "turn_id": turn_id,
       "chat_id": chat_id,
       "answer_text": answer_text,  # 内部含 [Elem#id]
       "evidences": evidences,
   }
   ```

验收点：

- 对同一 Chat 的多轮对话中：
  - 同一 `element_id` 的 `evidence_no` 在同一次响应中保持一致；
  - 新出现的 `element_id` 获得递增的编号；
- 数据库中：
  - `turns` 表 `answer_text` 字段保留 `[Elem#id]`；
  - `turn2element` 表仅包含真实引用的元素 ID。

---

## 8. 包 E：可选图像理解路径与配置开关

对应《dspy问答Agent设计.md》的 3.6–3.7。

### 8.1 视觉问答集成模块

在 `services/integrations/vision_vqa.py` 中实现：

```python
def vision_vqa_summarize(element_id: int, derived_question: str) -> str:
    """从 DB 读取 image_base64，调用 OpenAI 兼容视觉问答接口，返回文字摘要。"""
```

实现要点：

- 从 `ElementsRepository` 读取指定 `element_id` 的：
  - `image_base64`
  - `text_caption`
  - 可选：附近文本（如同一页面或同一 level_nav 范围内的其他元素）；
- 调用外部 VLM（通过统一 LLM/VLM 封装或 HTTP 客户端），构造图文 prompt；
- 返回对该图像的简要文字说明 `image_note`。

配置：

- 使用环境变量控制：
  - `VISION_VQA_ENDPOINT / VISION_VQA_MODEL / VISION_VQA_TIMEOUT_S / VISION_VQA_API_KEY / ...`；
- 在 `run_qa_turn` 中通过参数 `enable_image_vqa` 控制是否启用。

### 8.2 图像子问题生成 DSPy Program

在 `services/llm/` 中实现：

```python
def generate_image_question(question: str, memory_summary: str, local_context: str) -> str:
    """基于当前问题和局部上下文，为某张图片生成合适的视觉问答子问题。"""
```

输入：

- `question`
- `memory_summary`
- `local_context`：由 Python 侧构造，包含：
  - 图片 caption
  - 周边文本（基于 `level_nav` 和元素顺序选取）
  - 当前候选文本 evidence 摘要

输出：

- `image_question: str`

### 8.3 image_evidences 构造与 AnswerComposer 集成

在 `run_qa_turn` 中扩展：

1. 从候选 `candidates` 中筛选 `elem_type == "image"` 的元素；
2. 对每个候选图片：
   - 构造 `local_context`；
   - 调用 `generate_image_question` 得到子问题；
   - 调用 `vision_vqa_summarize(element_id, image_question)` 获得 `image_note`；
   - 构造 `EvidenceText`：

     ```python
     image_evidences.append(
         EvidenceText(
             element_id=img.element_id,
             elem_type="image",
             text_content=img.text_content + "\n" + image_note,
         )
     )
     ```

3. 将 `image_evidences` 传入 `AnswerComposer`。

降级策略：

- 若视觉问答调用失败：
  - 打日志并降级为仅使用 caption；
  - 不影响整体问答流程返回。

验收点：

- 开启 `enable_image_vqa=True` 时，针对含图片证据的问题：
  - Answer 中能体现来自图片的摘要信息；
- 关闭该开关时，流程退化为纯文本 RAG，仍然产出合理答案。

---

## 9. 人工验证与调试建议（供开发者手工执行）

> 注意：遵守仓库 Testing 指南，不使用 pytest、不构造 mock 数据。

### 9.1 手工调用链路

1. 在后端运行状态下，手工准备：
   - 至少一个真实 PDF 已通过 M2 流程入库为 `documents/elements`；
   - 对应元素已完成向量化（通过 M3 手工脚本或 `/api/retrieval/test` 验证）。
2. 调用：
   - `POST /api/collections` 创建 Demo 集合；
   - `POST /api/collections/{id}/documents` 上传 PDF（若尚未入库）；
   - `POST /api/collections/{id}/chats` 创建 Chat；
   - `POST /api/chats/{chat_id}/turns` 发起问题。
3. 检查：
   - 响应的 `answer_text` 中是否存在 `[Elem#id]`；
   - `evidences` 列表中的 `element_id/evidence_no/doc_id/page_index/bbox/elem_type/snippet` 是否合理；
   - 数据库中 `turns / turn2element` 写入是否符合规范。

### 9.2 建议的手工测试脚本（可选）

可在 `tests/manual/` 目录下增加独立 Python 脚本（仅供人工运行），例如：

- `tests/manual/test_m4_qa_flow.py`：
  - 使用真实数据库与 MinerU 输出；
  - 调用后端内部 `run_qa_turn` 函数；
  - 打印：
    - `question`
    - `answer_text`
    - 解析出的 `[Elem#id]` 列表
    - `evidences` 详细信息；
  - 不写入生产数据，仅在测试 Collection/Chat 上运行。

---

## 10. 里程碑拆分与时间顺序建议

1. **M4-A：路由 + Orchestrator 壳体 + schemas**
   - 目标：`POST /api/chats/{chat_id}/turns` 能返回占位数据；
2. **M4-B：历史加载 + MemorySummarizer**
   - 目标：请求日志中可看到 `history_text` 与 `memory_summary`；
3. **M4-C：RetrievalDecider + QueryRewriter + Retriver 集成**
   - 目标：针对典型问题，能看到合理的检索候选与 `text_evidences`；
4. **M4-D：AnswerComposer + evidence_mapper + turn/turn2element 持久化 + evidences 返回**
   - 目标：完整跑通文本 QA + Evidence 绑定链路，满足 DoD；
5. **M4-E：图像理解路径（可选开关）**
   - 目标：在启用图像理解时，回答中体现图片摘要信息；
6. **M4-F：端到端人工回归**
   - 目标：完成 1 套完整 Demo 脚本，从上传 PDF→向量化→提问→Evidence 高亮，准备后续 M5 前端联调的基础数据与接口。

以上即为 M4 阶段的详细执行计划，后续实现过程中如遇实际代码结构偏差，可在不改变核心职责边界与对外行为的前提下对模块命名与划分做小幅调整，并同步更新本计划与相关设计文档。 

