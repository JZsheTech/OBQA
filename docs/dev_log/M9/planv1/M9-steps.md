# M9 阶段执行步骤

1. **确认目标与范围**
   - 阅读 `docs/dev_log/M9/M9-plan-v1.md`，梳理 chunk 主索引、页级二段检索、回答链路锚点的要求。
   - 盘点现有解析/索引/检索代码，确定需要替换的元素级向量链路。
2. **数据层与配置改造**
   - 在 `schema.sql` 新增 `chunks` 与 `page_text_chunks` 表及索引，保留 elements 渲染字段。
   - `env_setting.py` 补充 chunk 构建与检索配置（最小字符、最大元素窗口、跳过模式、页级 topK 与开关）。
   - 新增仓储 `ChunksRepository` 与 `PageTextChunksRepository`，支持批量写入、向量更新、向量/全文/混合检索与页级过滤。
3. **索引链路重构**
   - 编写 `ChunkBuilder`：按 `level_nav` 窗口聚合文本元素，无 overlap，image/table 单元素单 chunk，并记录 `elem_ids/page_start/page_end`。
   - 重写 `DocumentIndexer`：重建 chunk/page_chunk、写库并使用嵌入服务生成向量；支持 collection 级重建。
   - 解析侧 `DocumentIngestor` 简化文本写入，`text_content` 与 `raw_text_content` 对齐，不再生成 header summary 或上下文 overlap。
4. **检索与 QA 链路切换**
   - `Retriever` 以 chunk 为主入口，支持页级二段过滤与 chunk→element 展开。
   - `QAOrchestrator` 用 chunk 结果组装 `[Elem#<id>] raw_text` 上下文，文本/图片证据分别限额，VQA 依旧可选。
   - `EvidenceText`/`evidence_mapper` 调整以新的锚点上下文输出。
5. **API 与文档同步**
   - 检索 API schema 切换到 chunk 结果，开放页级过滤参数。
   - 更新数据模型与系统设计文档，记录新表、chunk 构建/检索规则及配置项。
6. **静态校验与记录**
   - 运行静态编译检查（见 `M9-result-verify.md`），确认修改后的代码可通过语法校验。
