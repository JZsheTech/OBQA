# M10 重构统一计划 v1（单文档版）

> 只看本文件即可完成 M10 阶段重构（结合《多模态问答流程重构指南 v3》定稿、补充决策与提示词）。

## 目标与范围
- 聚焦问答主链：TextRetrieveAgent（dspy）、MemoryAgent（dspy）、可选 ImageRetrieveAgent、chunk→element 展开、候选合并去重、AnswerAgent（OpenAI VLM）、evidence_no 映射、turns.memory 维护与 turn2element 下线。
- 对齐前端控制面板：仅保留检索/记忆相关可调参数，默认值由后端提供。
- 产出可落地的接口、模块拆分与数据流，不引入 rerank/复杂策略，保持透明可调。

## 关键定案（含所有待确认项）
- 参数默认值/范围
  - 默认值：`use_image=false`，`text_retrieve_topk=8`，`image_retrieve_topk=2`，`text_memory_topk=4`，`image_memory_topk=1`，`use_page_in_text_retrieve=false`，`page_retrieve_topk=4`，`text_search_mode="hybrid"`。
  - 前端输入范围（建议）：TopK 类允许 1–20（步长 1），布尔用开关，`text_search_mode ∈ {hybrid, vector, fulltext}`。
- Memory 规格：`MEMORY_MAX_LEN=4000`，总结软限 `max_summary_memory_length=1000`，仅存一份 turns.memory。
- DSPy/LLM/Embedding：rewrite/summary/element 选择复用线上基座；embedding 用 `jina-embedding-v4`；文本链路默认 `x-ai/grok-4.1-fast:free`，`use_image=true` 且有图片时 AnswerAgent 切到 vision 模型 `x-ai/grok-4-fast`。
- AnswerAgent 提示词/打包：按docs/zh/工程细节/M10/多模态answerAgent提示词.md 《多模态answerAgent提示词.md》最终版执行（system + 结构化 user + image 顺序严格对应 ImageIndex）。
- 候选去重排序：按 element_id 去重；文本：检索得到的 element 维持相关性顺序，记忆返回的文本元素按给定顺序追加；图片同理。
- turn2element 历史数据：删除表后无需迁移，用户会手动重建数据库。
- ImageRetrieveAgent：rewrite/embedding 可复用文本策略，默认向量检索。
- evidence_no 一致性：单实例会话级缓存即可，不考虑多窗口并发。

## 流程总览（与 v3 对齐）
1) TextRetrieveAgent（dspy，必选，use_page_in_text_retrieve 控制页→chunk 二级检索）产出 `text_chunks`。  
2) ImageRetrieveAgent（可选，无 dspy，use_image=true 时启用）产出 `image_chunks`。  
3) MemoryAgent（dspy）：A) memory_generation（超长则总结）写 turns.memory；B) memory_selection 抽取 element_id。  
4) expand_chunk：根据 chunk.elem_ids 查 elements，产出 text_chunk_elements / image_chunk_elements。  
5) merge + dedup：`text_chunk_elements` + `image_chunk_elements`(可选) + `memory_text_elements` + `memory_image_elements`(可选)，按 element_id 去重并按上述排序策略拼接。  
6) AnswerAgent（OpenAI VLM）：输入 question + memory + merged elements（文本+图片），输出 answer_text + answer_evidence_ids；regex 兜底。  
7) evidence_no 映射：会话内首次 element_id → 递增编号，复用旧号；不落库，随会话销毁；返回 `answer` + `evidence_map`。

## 数据模型与持久化
- turns 表新增 `memory` 列（字符串，含 `[Elem#id]`）。每轮覆盖写入。
- turn2element 表删除：恢复历史时用 answer 中的 `[Elem#id]` 正则 + elements 查询。
- memory 入库前校验 `[Elem#id]`：正则提取 → DB 校验 → 无效 id 从文本移除 + warning 日志。
- 若需要升级脚本：仅新增列与删除依赖，不做历史迁移；不需要回滚

## 模块与实现要点（后端）
- TextRetrieveAgent（dspy）
  - 流程：query rewrite → 文本向量/全文/混合检索（受 `text_search_mode` 与 `use_page_in_text_retrieve/page_retrieve_topk` 控制）→ 截断 `text_retrieve_topk`。页检索开启时，先页 topK，再在页内取 chunk(按当前的做法加上一串限定页范围的filter)，整体不超 text_retrieve_topk。
  - 输出统一 `text_chunks`，包含 elem_ids 以便展开。
- ImageRetrieveAgent（可选，无 dspy）
  - use_image=true 时执行；复用文本 rewrite/embedding；默认向量检索；截断 `image_retrieve_topk`。
  - 输出 `image_chunks`（含 elem_ids）。
- MemoryAgent（dspy） 见 docs/zh/工程细节/M10/MemoryAgent提示词和规则.md
  - memory_generation：`last_memory + Q/A` 未超 `MEMORY_MAX_LEN` 则直拼；超限用给定 summary prompt（软限 1000）生成；对 `[Elem#id]` 校验清洗后写 turns.memory。
  - memory_selection：基于 question + last_memory 让 LLM 抽取 elem_id → 校验存在性 → 查表拆分 text/image；use_image=false 时图片列表置空。
- expand_chunk（无 dspy）
  - 输入 chunk 列表，批量按 elem_ids 查 elements，返回 element_id/type/doc_id/page_id/bbox/text_content/image_base64；缺失告警但不阻断。
- merge + dedup
  - 元素来源：text_chunk_elements，image_chunk_elements（可选），memory_text_elements，memory_image_elements（可选）。
  - 去重键：element_id。顺序：文本检索结果保持检索顺序 → 记忆文本按原顺序追加；图片同理。去重时保留首个出现项。
- AnswerAgent（OpenAI VLM，无 dspy）
  - 模型：`x-ai/grok-4-fast`。输入：question、memory（上一轮的turns.memory）、candidate elements (根据use_image决定是否使用image candidate elements)。
  - Prompt：使用《多模态answerAgent提示词.md》system+user 模板；`text_elements_serialized` 和 `image_elements_serialized` 按文档格式（含 `[Elem#id]`、ImageIndex 1-based、Caption 可空）；images 数组顺序与 ImageIndex 对齐。
  - 输出：结构化解析优先，失败时 regex 提取 `[Elem#id]`；返回 answer_text + answer_evidence_ids。
- evidence_no 映射
  - 会话内缓存 `element_id -> evidence_no`，递增分配；多实例无需一致；随会话结束释放。
- 参数配置（对齐前端）
  - 后端提供上述默认值并在接口返回；前端用户未设置则使用默认。
  - 统一校验范围与步长，避免非法值。
- 日志与健壮性
  - 记录阶段耗时、TopK 命中、无效 Elem#id、缺失 element、VLM 超长/失败重试、evidence_no 分配情况。异常不应中断主链（除硬性依赖故障）。

## 前端需求
- QA 控制面板：保留/新增 `use_image`、`text_retrieve_topk`、`image_retrieve_topk`、`text_memory_topk`、`image_memory_topk`、`use_page_in_text_retrieve`、`page_retrieve_topk`、`text_search_mode`；移除“检索模式（强制/直接回答）”与“历史轮数”。
- 默认值从后端读取，用户修改后覆盖；TopK 输入范围按后端校验一致。
- Answer/Evidence 展示：支持 `answer` + `evidence_map`；和当前前端保持一致。

## 里程碑建议（可逐步推进）
1. W1：turns.memory 字段与清洗逻辑、移除 turn2element 依赖、检索接口草稿与参数默认值对齐。
2. W2：TextRetrieveAgent/MemoryAgent（dspy）落地，ImageRetrieveAgent（可选）对齐检索接口，chunk→element 展开完成。
3. W3：AnswerAgent（VLM）接入、evidence_no 映射、前后端参数/展示联调。
4. W4：日志与健壮性收尾、手动验证脚本、docs 更新（中/英文关键文件）。

## 手动验证（符合仓库测试要求）
- 不使用 pytest；编写独立 Python `main()` 脚本，覆盖：文本/图片检索链路、记忆更新/检索、候选合并去重、AnswerAgent 调用、evidence_no 映射。
- 使用真实样本数据（`sample_data/` 或新 PDF）；打印关键日志（TopK、抽取到的 elem_id、去重结果、VLM 返回的 evidence_id）。
- 不写入生产库；人工查看打印输出验证逻辑一致性。

## 依赖与风险
- 依赖：MinerU/OceanBase 正常可用；DSPy/LLM/embedding 需提前配置（jina-embedding-v4 + x-ai/grok-4-fast）。已经人工验证通过
- 风险：无效 elem_id 清洗可能导致记忆信息损失，需日志可追溯。
