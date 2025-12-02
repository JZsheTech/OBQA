# M10 阶段重构计划（基于《多模态问答流程重构指南 v3》）

## 目标与范围
- 聚焦问答主链：TextRetrieveAgent（dspy）、MemoryAgent（dspy）、可选 ImageRetrieveAgent、Chunk→Element 展开、候选合并去重、AnswerAgent（OpenAI VLM）、evidence_no 映射、turns.memory 维护与 turn2element 下线。
- 对齐前端控制面板：新增/保留的检索与记忆配置参数，对齐后端默认值。
- 输出工程可落地的接口、模块拆分与数据流，避免 rerank/复杂策略，保持透明可调。

## 里程碑（建议节奏）
1) W1：数据库/模型调整（turns.memory、移除 turn2element 读写）、基础检索链路梳理、参数面板接口草稿。
2) W2：TextRetrieveAgent/MemoryAgent（dspy）落地，ImageRetrieveAgent（可选）对齐检索接口，Chunk→Element 展开与候选合并去重实现。
3) W3：AnswerAgent（OpenAI VLM）接入与 evidence_no 映射，前端参数面板与 evidence 显示联调。
4) W4：日志与健壮性收尾、手动验证脚本、文档更新（中/英文关键文件）。

## 工作拆解
### 后端
- 数据库与模型
  - 在 `turns` 表新增 `memory` 字段，数据库SQL接口同步；新增/更新写入链路：memory_summary 入库前做 Elem#id 校验与清洗。
  - 停用 turn2element：移除写入路径与依赖，历史数据读取改为从 answer 正则抽取再查 elements。@todo[6]
  - 设计升级脚本（或数据迁移策略）与回滚方案，避免生产数据丢失。@todo[6]
- TextRetrieveAgent（dspy）
  - 流程：query rewrite（dspy）→ 文本向量检索（支持 use_page_in_text_retrieve/page_retrieve_topk/text_search_mode）→ 截断 text_retrieve_topk。
  - 输出统一 `text_chunks` 结构，携带内部 elem_ids 供展开。
  - 确认 dspy 模型/模板、检索接口（向量/全文/混合）与 embed 模型。@todo[3]
  - 若开启 page 检索，按页→chunk 二级检索，保持 topk 约束。
- ImageRetrieveAgent（可选，无 dspy）
  - 仅 use_image=true 时运行；流程：query rewrite（可共用或独立策略）→ 图片向量检索 → `image_chunks`。
  - 默认向量检索模式；确认是否需要独立 rewrite/embedding。@todo[7]
- MemoryAgent（dspy）
  - 记忆更新：`last_memory + 当前Q/A` 超长则 LLM 总结；正则提取 Elem#id，落库前校验，不存在则删除并告警。
  - 记忆检索：从 memory 中抽取 element_id → DB 校验 → 输出 text/image 元素（image 在 use_image=false 时丢弃）。
  - 确定 MEMORY_MAX_LEN 与总结提示词/模型。@todo[2][3]
- Chunk→Element 展开
  - 提供统一 `expand_chunk`，按 elem_ids 取 elements 表，返回 element_id/type/doc_id/page_id/bbox/text_content/image_base64。
  - 需要快速批量查询与缺失兜底（缺失记录告警，不阻断流程）。
- 候选合并去重
  - 输入 text_chunk_elements + image_chunk_elements（use_image 时）+ memory_text_elements + memory_image_elements（use_image 时）。
  - 按 element_id 去重，保留原序/得分的稳定顺序策略。@todo[5]
- AnswerAgent（OpenAI VLM，无 dspy）
  - 输入 question + memory_summary（turns.memory）+ candidate_elements + use_image。
  - 打包元素文本/图片入 VLM，提取 answer_text 与 answer_evidence_ids（结构化或 regex）；异常时回退 regex 提取。
  - 需要确定 VLM 提示词格式、元素拼接格式、图片传输方式与长度截断策略。@todo[4]
- evidence_no 映射
  - 会话级内存映射：首见 element_id → 递增编号；后续复用；不落库，随会话丢弃。
  - 对接前端返回 `answer` + `evidence_map`。
  - 跨进程/多实例会话一致性策略待定。@todo[8]
- 参数配置
  - 后端提供默认值：use_image、text_retrieve_topk、image_retrieve_topk、text_memory_topk、image_memory_topk、use_page_in_text_retrieve、page_retrieve_topk、text_search_mode。
  - 未指定的默认值需决策并暴露给前端。@todo[1]
- 日志与健壮性
  - Elem#id 校验失败告警、缺失 element 告警、VLM 超长/失败重试、各阶段耗时与 TopK 命中率日志。

### 前端
- QA 控制面板
  - 保留/新增：use_image、text_retrieve_topk、image_retrieve_topk、text_memory_topk、image_memory_topk、use_page_in_text_retrieve、page_retrieve_topk、text_search_mode。
  - 移除：检索模式（强制检索/直接回答等）、历史轮数。
  - 默认值读取后端配置，前端仅覆盖用户手动设置。
  - 需要确认数值范围/步进及 UI 呈现方式。@todo[1]
- Answer/Evidence 展示
  - 支持 `answer` + `evidence_map`，展示 evidence_no 与 Elem#id 绑定；点击跳转/高亮时按 element_id 查询。
  - 处理 use_image 场景下的图片 evidence 显示。

### 验证与交付
- 手动验证脚本（独立 Python main）：覆盖检索链路、记忆更新/检索、Candidate 合并、AnswerAgent 调用、evidence_no 映射。
- 使用真实样本数据（sample_data 或新 PDF），打印日志供人工检查；不写入生产库。
- 更新 `docs/` 下相关架构与控制面板说明；记录参数默认值、接口示例。

## 依赖与风险
- 依赖 MinerU/OceanBase 正常可用；DSPy/LLM 配置需提前可用。@todo[3]
- 风险：VLM 输入超长、元素缺失导致答案引用失效、跨实例 evidence_no 不一致；需在实现/运维中加兜底与监控。@todo[4][8]

## 对应待决策项
- 详细不确定项见 `docs/dev_log/M10/M10_to_check.md`（@todo 列表），需产品/架构确认后落定。
