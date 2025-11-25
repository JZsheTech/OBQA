# 问答 Agent 流程

## 后端接收 question 时的执行链路
- **入口与参数**：前端调用 `POST /api/chats/{chat_id}/turns`，携带 `question` 以及可选的 `top_k`（1~20 取整）、`enable_image_vqa`、`enable_memory_summarizer`。接口返回 `answer_text`（包含 `[Elem#id]`）、`evidences`（带元素元数据）、`answer_with_evidence`（替换为 `[Evidence#no]`）。
- **Chat 与上下文解析**：`QAOrchestrator` 根据 chat 类型解出 `collection_id/doc_id`，读取历史 `turns`，用 `format_history_text` 生成最近 `max_history_turns=8` 轮的转录文本；若开启 `enable_memory_summarizer`，则走 `MemoryService` 调用 DSPy 总结。
- **检索决策与 query 改写**：`RetrievalDecider`（DSPy 签名，失败回退启发式）决定 `need_retrieve` 及元素类型过滤（默认为 text/header/table/image）。若需要检索，`QueryRewriter` 在问句和历史摘要基础上生成 search query（失败则用原问句+摘要前缀）。
- **检索与证据准备**：`Retriever` 调用 `EmbeddingService` 走 OpenAI 兼容 `/v1/embeddings`，向 OceanBase `elements` 做向量或全文检索，top_k 受限于用户参数和 `text_evidence_limit=8`。文本类元素直接加入 `text_evidences`；命中的 image 元素先收集为候选。
- **可选视觉路径**：对图片候选（最多 `image_evidence_limit=4`），`ImageQuestionGenerator` 生成派生子问句；若开启 `enable_image_vqa` 且存在 `VisionVQAClient`，读取 `image_base64` 调用视觉接口得到摘要，与 caption/局部上下文拼接为 image evidence；否则仅用 caption/上下文。
- **回答生成**：`AnswerComposer` 将 question、memory summary、文本/图片 evidences 组合为 DSPy prompt，要求按 `[Elem#<id>]` 引用；异常或无证据时回退为首个 evidence 片段或“暂无足够证据”的提示。
- **落库与编号**：计算 turn order，写入 `turns` 并更新 chat；用正则解析 `answer_text` 中的 `[Elem#id]` 批量写 `turn2element`。然后对历史所有元素构建 `element_id→evidence_no` 映射，加载元素元数据，生成 `evidences` payload（含 doc/page/bbox/title/snippet）。

```
前端提问
　│
　▼
POST /api/chats/{chat_id}/turns
　├─ 参数：question + top_k + enable_image_vqa + enable_memory_summarizer
　▼
QAOrchestrator
　├─ 读取 chat 历史（最近最多8轮）
　└─ 若开记忆总结 → MemoryService (DSPy) 生成历史摘要
　▼
RetrievalDecider (DSPy)                  ←失败→ 走启发式规则
　└─ 判断 need_retrieve + 元素类型过滤（text/header/table/image）
　　　　│
　　不需要检索 ───────────────────┐
　　　　│                          ▼
　　　　▼                     AnswerComposer
　需要检索                      （直接用历史/记忆回答）
　　│
　　▼
QueryRewriter (DSPy)               ←失败→ 直接用原问题+历史摘要
　　└─ 生成最终 search query
　　　　▼
Retriever
　　└─ EmbeddingService → OceanBase 向量/全文检索
　　　　└─ 取出 top_k 文本元素（≤8） → text_evidences
　　　　└─ 取出图片候选（≤4）
　　　　　　│
　　　　　　▼
　　　　有图片且 enable_image_vqa？
　　　　　　├─是 → ImageQuestionGenerator 生成子问题
　　　　　　│       → VisionVQAClient 视觉问答
　　　　　　│       → 得到图片描述 + caption + 上下文 → image_evidences
　　　　　　└─否 → 只用 caption + 局部上下文作为 image_evidences
　　　　　　　　▼
　　　　　　AnswerComposer (DSPy)
　　　　　　　├─ 输入：question + 历史/记忆摘要 + text_evidences + image_evidences
　　　　　　　├─ 输出：answer_text（必须包含 [Elem#id] 引用）
　　　　　　　└─ 若异常或无证据 → 回退提示
　　　　　　　　▼
　　　　　　正则解析 answer_text 中的 [Elem#id]
　　　　　　　　▼
　　　　　　写入 DB
　　　　　　　├─ 新建 turn
　　　　　　　├─ 写入 turn2element 关联表
　　　　　　　└─ 构建 element_id → evidence_no 映射
　　　　　　　　▼
　　　　　　返回给前端
　　　　　　　├─ answer_text（带 [Elem#id]）
　　　　　　　├─ answer_with_evidence（替换为 [Evidence#1]）
　　　　　　　└─ evidences（完整元数据：doc/page/bbox/snippet 等）

```



# 改进要求:

目标：让问答链路的检索/记忆/视觉开关具备“系统默认（env_setting.py）+ 单轮覆盖（前端传参）”的双层控制，并保持与现有接口的向后兼容。

- 后端默认配置（EviQAsys/backend/app/env_setting.py）
  - 增加 `QAFlowSettings`（或同名结构）与 `get_qa_flow_settings()`，集中声明 QA 相关默认值并允许环境变量覆盖：`QA_MAX_HISTORY_TURNS`（默认 8）、`QA_TEXT_EVIDENCE_LIMIT`（8）、`QA_IMAGE_EVIDENCE_LIMIT`（4）、`QA_ENABLE_MEMORY_SUMMARIZER`（False）、`QA_ENABLE_IMAGE_VQA`（False）、`QA_DEFAULT_RETRIEVAL_MODE`（auto|force|skip，默认 auto）、`QA_DEFAULT_SEARCH_MODE`（vector|fulltext，默认 vector）、`QA_DEFAULT_ELEM_TYPES`（逗号分隔，默认 text,header,table,image）。`QAFlowConfig` 的默认值需与这里保持一致。

- 请求/响应契约（EviQAsys/backend/app/schemas/qa.py + api/routes/chats.py）
  - 在 `TurnCreateRequest` 增加可选字段：`retrieval_mode`（Literal["auto","force","skip"]）、`elem_types`（list[str]）、`search_mode`（Literal["vector","fulltext"]）、`max_history_turns`（int >=0）、`enable_image_vqa`、`enable_memory_summarizer`。旧字段默认行为不变，未提供时走 env 默认。
  - 在 `create_turn` 路由中读取上述字段，传入 `run_qa_turn`。保持 top_k 处理逻辑不变（1~30 取整，默认 8）。
  - `run_qa_turn` / `QAOrchestrator` 构造时注入 `QAFlowSettings`，并接受每次请求的临时覆盖值。

- QAOrchestrator 执行逻辑（EviQAsys/backend/app/services/qa_flow/qa_orchestrator.py）
  - 引入 per-turn 配置来源（请求字段优先，其次 env 默认），覆盖 `max_history_turns`、`enable_memory_summarizer`、`enable_image_vqa`、`text_evidence_limit`、`image_evidence_limit`。
  - 新增 `retrieval_mode` 分支：`skip` 直接跳过 `RetrievalDecider` 与检索，使用历史/记忆直接回答；`force` 固定 `need_retrieve=True`，`elem_types` 优先用请求字段，否则用 `RetrievalDecider` 结果；`auto` 维持现有决策流程。
  - 将 `elem_types`/`search_mode` 透传到 `Retriever.retrieve_topk`（当前 retriever 已支持 search_mode 参数），并在日志中记录最终采用的模式与类型。
  - VQA 路径默认值取自 env，可被请求字段覆盖；仅在最终 enable_image_vqa=True 时实例化 `VisionVQAClient`。

- 前端控制面板（EviQAsys/frontend）
  - 在 `src/api/client.js` 的 `createTurn` 请求中增加 `retrieval_mode`、`elem_types`、`search_mode`、`max_history_turns`、`enable_image_vqa`、`enable_memory_summarizer` 参数（保持 snake_case 与后端一致，未填写不传）。
  - 在聊天页面（`src/pages/CollectionChat.jsx` / `DocumentChat.jsx` 或共享组件）新增交互控件：检索模式选择器（auto/force/skip）、搜索模式（vector/fulltext）、模态多选（text/header/table/image/equation）、历史轮数输入、记忆摘要开关、视觉问答开关。默认值与 env_setting 中保持一致，提交时组装到 `createTurn` 请求体。
