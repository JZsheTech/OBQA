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

## 简化与加速建议（兼顾用户可自定义）
- **显式检索开关**：在 `TurnCreateRequest` 增加 `retrieval_mode`（`auto`|`force`|`skip`）或 `need_retrieve` 布尔，允许用户直接跳过 embedding+DB 检索（仅用历史/提示）或强制检索以避免 DSPy 决策误判。
- **自定义检索范围**：开放 `elem_types`、`search_mode`（vector/fulltext）和 `text_evidence_limit/image_evidence_limit` 作为请求级参数，避免无关图片/表格进入 pipeline，减少 embedding/排序开销。
- **历史窗口可调**：将 `max_history_turns` 暴露为参数或在 chat 级配置，便于用户选择“零上下文”快速模式或“长记忆”模式；关闭 `enable_memory_summarizer` 时可直接截断到 N 轮以省一次 DSPy 调用。
- **视觉路径懒加载**：目前 `enable_image_vqa` 全局开启即对所有图片候选调用视觉接口。可改为：先用文本 evidence 判断是否已足够，否则再按优先级对少量图片触发 VQA；或提供 `image_strategy`（`none`|`caption_only`|`vqa_if_needed`|`vqa_all`）让用户控制延迟和成本。
- **快速回答通道**：当 `decision.need_retrieve=False` 或检索命中为空时，可在 `AnswerComposer` 中提供轻量 prompt 模板，直接基于问题与历史返回“无证据回答/澄清问题”，避免重复 embedding 或长 prompt 构造。
- **缓存与复用**：对相同 chat 的最近一次 embedding 结果与 evidence 列表做短期缓存（按 question hash + collection/doc id），复用在短时间的追问中；同时缓存 `image_base64` 加载结果，减少对 OceanBase 的重复读取。
- **响应裁剪**：限制传给 DSPy 的 evidence 文本长度（现有 800 字符截断可在配置中暴露）并对 `answer_text` 进行简短化选项，提供“简洁模式”以减少模型推理时间与前端渲染负担。

# 改进要求:


