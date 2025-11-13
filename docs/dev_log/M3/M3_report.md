## M3 阶段实施报告

### 核心改动
1. **配置**：`VECTOR_DIM` 默认值调整为 2048，并在 `env_setting.py` 新增 `EmbeddingSettings`（endpoint/model/timeout/retry/API key 等），供嵌入服务与脚本共享。
2. **嵌入封装**：`services/embedding/embedding_service.py` 封装 OpenAI 风格请求，支持文本 + 图像消息体、重试、维度校验，并提供 `batch_embed_elements()` 方便批量写入。
3. **仓储扩展**：`ElementsRepository` 增加 `list_unembedded`、`update_embeddings`（CAST 为 `VECTOR`）、`topk_by_collection`（Python 侧 cosine 相似度）以及 `search_fulltext` 兜底查询。
4. **检索服务与 API**：`services/retrieval/retriever.py` 统一查询入口，新增 `GET /api/retrieval/test` 返回 `{code,data}`；支持 `collection_id` + 可选 `doc_id/elem_types` + `search_mode=vector|fulltext`。
5. **手工脚本**：`tests/manual/test_m3_embedding_and_retrieval.py` 补齐缺失向量并打印 TopK 结果（含 score/page/bbox 预览），可配置 batch size、检索模式与元素类型过滤。
6. **文档**：`README.md`、`docs/zh/技术栈.md`、`docs/zh/开发路线图.md` 补充嵌入配置、检索流程与手工验证指引。

### 使用建议
1. 启动 OceanBase + MinerU + vLLM 后，设置 `EMBEDDING_*` 环境变量并确保 `VECTOR_DIM` 与模型维度一致。
2. 执行 `python EviQAsys/backend/tests/manual/test_m3_embedding_and_retrieval.py --collection-id <id> --query "<question>"`，脚本会：
   - scanning `vec_embedding IS NULL` rows 分批嵌入并记录维度；
   - 输出 `Retriever` TopK 结果，包含 `doc_id/page_no/bbox/elem_type/score/text preview`。
3. 后端启动后，可通过 `GET /api/retrieval/test?collection_id=<id>&query=...&top_k=5` 与可选 `doc_id / elem_types / search_mode` 做联调。

> 若后续接入 OceanBase 原生向量函数，可在 `ElementsRepository.topk_by_collection()` 中替换为 SQL 侧计算并保留现有 Python 逻辑作为兜底。
