# M4 启动前需确认的问题清单（请开发者答复）

为降低在问答主干（DSPy 文本编排 + Evidence 锚点绑定）阶段的返工风险，基于《开发路线图（M4）》与《M4_refactor_doc.md》、数据模型与设计文档，整理出目前看起来仍需澄清的关键技术点如下。

## DSPy 编排与 LLM 集成

- DSPy 模块拆分：M4 是否同意采用“问句重写模块 + 回答模块”两段式 DSPy 编排（Python 侧 `qa_flow` 显式先调用 rewrite，再用 rewritten_query + 检索结果调用 answer），而不是在一个 Signature 内同时做重写+回答？（前者更方便单独调试与替换。）
- 文本 LLM 后端：目前 `env_setting` 已有 `OLLAMA_OPENAI_BASE_URL`。是否约定 DSPy 统一通过该 OpenAI 兼容端点调用，并用一个环境变量（如 `QA_LLM_MODEL`）指定模型名？还是希望问句重写和回答可以使用不同模型？

## Evidence 锚点与存储策略

- `turns.llm_answer_text` 的存储格式：DB 中是保留原始 LLM 输出（含 `[Elem#id]`），API 在返回时临时替换为 `[Evidence#no]`，还是希望 DB 里直接保存已经替换过的展示文本？（前者更利于回放和重新构建 evidence 映射。）
- Evidence 编号的“历史序列”来源：目前既可以基于 `turn2element`（按 `chat_id + turn_order` 排序得到的 element_id 序列）构建，也可以按照 M4_refactor_doc 的说法，从历史 `llm_answer_text` 中用正则抽取 `[Elem#id]` 再去重。更偏向哪一种作为唯一事实来源？（我倾向于以 `turn2element` 为准，与桥表职责一致。）
- `turn2element` 写入范围：是否只为“答案文本里真实出现的 `[Elem#id]`”写记录，而不为未被引用但参与上下文的候选元素写入？（数据模型的表述更偏向“只记录真实引用”，这里希望确认。）

## Chat 记忆与上下文构造

- 记忆窗口：路线图建议“仅拼接最近若干轮（例如 3 轮）”。M4 是否可以先实现“只取最近 N=3 轮问答作为上下文”，暂不做历史摘要；等对话长度真的成为问题时再单独引入 summarization？
- 如需在 M4 就落地“历史摘要”，是否偏向：A）将摘要作为一个特殊 turn 写入 `turns` 表（可带标记字段）；B）在 `chats` 增加 `summary_text` 字段？（涉及是否要调整数据模型。）

## API 形态与返回结构

- `POST /api/chats/{chat_id}/turns` 响应中的 `anchors` 字段：最终期望结构是仅返回 `[{evidence_no, element_id}]` 这样的轻量列表，还是希望返回完整的 evidence 信息（含 `doc_id/page_no/bbox/snippet`）？这会影响与 `GET /api/turns/{turn_id}/evidences` 的职责划分。
- `GET /api/turns/{turn_id}/evidences` 的范围：是只返回“当前 turn 的 evidences”，还是返回“整个 chat 的 evidences（带当前 turn 标记）”？前者更简单，后者方便前端做“全局证据列表”，需要明确。
- 是否需要在上述 API 的 `data` 中附带可选的调试信息（例如 `rewritten_query`、`used_element_ids`、`llm_model`），统一放在 `debug` 字段下，供 M4 手工测试脚本和前端调试面板使用？

## 图像理解（可选路径）

- M4 DoD 中的图像理解路径是否为“强制实现”，还是可以作为一个 feature flag：默认仅使用 caption 参与回答，`vision_vqa_summarize` 初期可以是占位实现（始终返回空字符串或提示语）？
- 若开启图像 VQA，VQA 摘要与 caption 拼接后的文本是只在一次回答流程中临时使用，还是需要回写到 DB（例如更新 `elements.text_content` 或新增 `image_summary` 字段）以便下次复用？

## 失败与降级策略（锚点相关）

- 当 LLM 输出的锚点有问题（完全没有 `[Elem#id]`，或包含不在候选列表中的 `element_id`）时，预期的降级策略是什么：A）仍返回答案文本但不写 `turn2element`，前端只显示无 Evidence 的回答；B）视为业务错误直接返回 4xx/5xx；C）自动按检索 TopK 补一份 evidence 列表但不在文本中替换？希望确认一个主方案，方便统一实现 evidence 相关的异常处理。

—— 请在以上问题处逐条确认或给出偏好，我们会据此收敛 M4 的具体实现细节并开始编码。

