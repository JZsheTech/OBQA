# seekdb 内置混合检索替换计划（chunks/检索层）

- 背景：当前混合检索在应用层分别做全文 + 向量检索并在 Python 中融合评分，规模增大后效率与召回/精度存在上限。
- 目标：将“混合检索”切换为 seekdb 内置 `DBMS_HYBRID_SEARCH.SEARCH`，保留现有 API 输出结构与调用入口不变。
- 范围：后端检索层 `ChunksRepository.search_hybrid` 为主，必要时补齐 DDL（vector/fulltext 索引）与配置；可选同步 `ElementsRepository.search_hybrid`。

## 1. 里程碑（阶段划分）
- M1（设计&验证）：
  - 读懂 `dependency/oceanBaseDemo/oceanbase_seekdb_demo/hybrid_search.py` 与 `demo8_hybrid_search_seekdb.py` 的 SQL 形式。
  - 验证 seekdb 是否支持 JSON 参数中的过滤条件（collection_id/doc_id/chunk_type/page）。
- M2（代码改造）：
  - 改造 `ChunksRepository.search_hybrid` 调用 seekdb 内置混合检索并解析 JSON 结果。
  - 新增配置项与降级策略（seekdb 不可用时回退到 Python 融合）。
- M3（索引与验证）：
  - 更新 schema/DDL 以支持 vector + fulltext 索引。
  - 新增手动测试脚本 + 测试说明，基于真实 PDF 解析数据。

## 2. 任务拆分（重点变更点）
1) 检索接口替换
   - 在 `EviQAsys/backend/app/repositories/chunks_repo.py` 中：
     - 将 `search_hybrid` 改为调用 `DBMS_HYBRID_SEARCH.SEARCH`。
     - 通过 `json.dumps(param)` 构造查询参数（参考 `dependency/oceanBaseDemo/oceanbase_seekdb_demo/hybrid_search.py`）。
     - 将返回 JSON（list[dict]）解析为现有行结构，映射 `_score -> score`，并复用 `_format_row`。
   - 建议保留旧逻辑为私有方法（如 `_search_hybrid_python`），在 seekdb 不可用/异常时自动降级。

2) 参数与过滤策略
   - Param 建议结构：
     - `query.query_string.fields`：优先 `chunk_text_main`（可选加入 `level_nav`）。
     - `query.query_string.query`：用户 query。
     - `query.query_string.boost`：文本权重（可配置）。
     - `knn.field`：`vec_embedding`。
     - `knn.k`：top-k（可按过滤场景适当放大）。
     - `knn.query_vector`：embedding 向量。
     - `knn.boost`：向量权重（可配置）。
   - 过滤条件：
     - 先验证 seekdb 是否支持 JSON 过滤（如 bool/filter/term 语法）。
     - 若不支持过滤：在 Python 侧对结果进行 `collection_id/doc_id/chunk_type/page_filters` 过滤，并在查询时扩大 `k`（例如 `k * 3` 或 `k + 50`）防止过滤后不足。

3) 配置项与可控性
   - `EviQAsys/backend/app/env_setting.py` 新增：
     - `HYBRID_SEARCH_BACKEND=seekdb|python`（默认 seekdb）。
     - `HYBRID_TEXT_BOOST`、`HYBRID_VECTOR_BOOST`（默认 2.0/1.0 或与现有权重等价）。
     - `HYBRID_K_MULTIPLIER`（过滤场景结果放大倍数）。
   - `EviQAsys/backend/app/template_config.yaml` 增加对应注释项。

4) 数据库索引与 Schema 更新
   - 在 `EviQAsys/backend/app/repositories/sql/schema.sql` 增加（按需）：
     - `CREATE VECTOR INDEX` on `chunks(vec_embedding)`。
     - `CREATE FULLTEXT INDEX` on `chunks(chunk_text_main)`（或 `chunk_text_main, level_nav`）。
     - 若后续 elements 也用 hybrid：为 `elements(vec_embedding)` 与 `elements(text_content, text_caption)` 增加索引。
   - 对已存在数据库：补充手动 DDL 说明（或新增一次性迁移脚本）。

5) 结果映射与兼容性
   - Seekdb 返回字段包含整表列（含 `vec_embedding`）；需要在仓库层手动投影。
   - `elem_ids` 可能以 JSON 字符串返回，需复用 `_deserialize_elem_ids` 解析。
   - 评分尺度与旧逻辑不同，确认 `Retriever` 使用 `_score` 即可（无需二次融合）。

6) 文档同步
   - 更新 `docs/` 内与检索相关的描述（如有），注明混合检索已切换到 seekdb 内置 API。

## 3. 手动测试脚本（新增）
- 文件建议：`EviQAsys/backend/tests/manual/test_seekdb_hybrid_search.py`
- 目标：
  - 使用真实 PDF（`sample_data/pdf_doc/...`）完成 ingestion + chunk embedding。
  - 以 `search_mode=hybrid` 调用 `Retriever.retrieve_topk`，输出 top-k chunk 的 `_score/score` 与文本片段。
  - 验证 seekdb 内置混合检索结果可用且字段映射正确。
- 脚本要求：
  - 必须含 `main()` 与 `if __name__ == "__main__": main()`。
  - 不能使用 pytest；不能用 mock 数据。
  - 不写入生产数据库：运行前要求设置 `OB_DEFAULT_DATABASE` 为测试库或显式 `--reset-db`。

## 4. 手动测试说明（执行步骤）
1) 准备环境
   - 启动 seekdb/oceanbase，确认 `DBMS_HYBRID_SEARCH` 可用。
   - 确认 `chunks` 表已建立 vector + fulltext 索引（或运行 DDL）。

2) 运行测试脚本
   - 示例命令：
     - `python EviQAsys/backend/tests/manual/test_seekdb_hybrid_search.py \
        --pdf-dir sample_data/pdf_doc/RL_paper_small \
        --question "Summarize the key contributions" \
        --top-k 8 \
        --reset-db`
   - 脚本应打印：
     - 目标数据库/collection_id
     - 检索 top-k 结果（chunk_id、score、chunk_text_main 前 200 字）
     - 过滤条件命中数量（若启用 page_filters/chunk_types）

3) 验证点（人工确认）
   - 结果数量：>= top-k（过滤后不足需提示）。
   - 分数排序：`score` 单调递减。
   - 文本相关性：top-k 前几条应与 query 主题匹配。
   - 若关闭 seekdb（或配置 `HYBRID_SEARCH_BACKEND=python`），应能回退旧逻辑正常运行。

## 5. 风险与缓解
- seekdb 混合检索 JSON 过滤语法不兼容 → 先验证支持；否则回退 Python 过滤 + 扩大 k。
- 评分尺度变化影响排序/阈值 → 将 score 直接透传，并记录变更说明；必要时调整 top-k 或权重。
- 索引未创建导致性能/结果异常 → 在 schema.sql 补充索引 + 在手测前明确检查步骤。
- 兼容性风险（OceanBase 社区版无 DBMS_HYBRID_SEARCH） → 通过配置开关与异常捕获降级。

## 6. 交付物清单
- 代码：`chunks_repo.py` 混合检索替换 + 配置项 + 解析映射逻辑。
- DDL：schema.sql 增加 vector/fulltext 索引（或补充迁移说明）。
- 手动测试：新增 `test_seekdb_hybrid_search.py` 脚本 + 运行说明。
- 文档：更新相关 dev_log/架构说明，记录改造与验证结论。
