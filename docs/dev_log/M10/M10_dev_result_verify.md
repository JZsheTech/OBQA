# M10 开发结果与手工验证记录

## 本次改动快照
- 后端 QA 主链对齐《M10 重构统一计划》：重写 `QAOrchestrator` 为 Text/Image/Mem → expand → merge → AnswerAgent(VLM) 流程；文本检索支持页级过滤，图像检索独立开关；记忆生成/抽取统一走 turns.memory，按 `[Elem#id]` 校验清洗。
- 数据模型：`turns` 增加 `memory` 列；初始化时自动删除 `turn2element`；维护脚本/默认清理顺序同步去掉 turn2element。
- 配置与 API：新增 M10 默认参数（use_image、text/image retrieve/memory topk、page_retrieve_topk、text_search_mode），在 `ChatDetail.qa_config_defaults` 返回；`/chats/{id}/turns` 请求/响应字段改为上述参数 + `evidence_map`。
- 前端：Collection/Document Chat 控制面板精简为 M10 参数（文本/图片检索与记忆 TopK、页过滤开关、检索模式、use_image），默认值跟随后端；移除检索模式开关/历史轮数/强制检索等旧控件。

## 手工验证计划（仅手工，需真实数据）
> 不使用 pytest；每个脚本需具备 `main()` 入口，读取真实 MinerU/OceanBase 数据或 `sample_data/` 中的 PDF。

1. **数据库结构检查**
   - 运行 `python scripts/reset_database.py --skip-uploads` 初始化表。
   - 手工确认 `turn2element` 表已删除，`turns` 表含 `memory` 列。
2. **检索链路（文本/图片）**
   - 编写 `tests/manual_m10_retrieval.py`（带 `main()`），调用 `Retriever.retrieve_topk` 与 `TextRetrieveAgent/ImageRetrieveAgent` 对真实 collection 进行查询，打印 rewrite 后 query、命中 chunk ids、elem_ids、page 过滤情况。
   - 使用 `use_page_in_text_retrieve=True/False`、`text_search_mode=hybrid/vector/fulltext` 对比 TopK 命中差异。
3. **记忆生成与抽取**
   - 手工脚本 `tests/manual_m10_memory.py`：构造带 `[Elem#id]` 的 memory + QA，调用 `MemoryAgent.generate_memory`，验证超长时触发总结且无效 id 被清除（打印前后 memory 及移除 id）。
   - 通过 `MemoryAgent.select_elements` 在 `use_image` 开关下输出 text/image elem_id 列表，确认不存在的元素被丢弃并记录 warning。
4. **AnswerAgent & evidence 映射**
   - 在已有元素的 chat 上调用 `/chats/{id}/turns`，问题需引用真实元素；检查响应 `answer`、`evidences`、`evidence_map`，并确认 `answer_with_evidence` 标签顺序与映射一致。
   - 如果模型不可用，可用最小 mock 文本替代调用路径，重点核对 `[Elem#id]` 提取、去重合并与 evidence_no 递增逻辑。
5. **前端联调**
   - 打开 Collection/Document Chat，确认控制面板仅包含 M10 参数，默认值与后端 `qa_config_defaults` 对齐；切换 use_image/TopK 后提问，前端可展示 `evidence_map` 对应的 Evidence 标签并跳转高亮。

### 当前状态
- 未执行自动化测试，按仓库要求仅给出手工验证方案。
- 所有改动均保持在工作区，未提交。
