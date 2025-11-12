# M3 计划：Embedding & Retrieval（向量化与检索）

## DoD（完成准则）
- 后端脚本或 API 可对新入库的 elements 计算向量，并写入 `elements.vec_embedding`。
- `GET /api/retrieval/test`（或等价脚本）可基于查询返回 TopK 候选 elements，附带必要元数据。

## 交付物
- 后端嵌入封装：`services/embedding/embedding_service.py`（兼容 OpenAI `/v1/embeddings` 流程，支持文本/多模态）。
- 检索服务：`services/retrieval/retriever.py`（生成查询向量 + TopK 相似度检索）。
- 仓储扩展：`ElementsRepository` 新增写入 `vec_embedding` 与 TopK 相似度检索的简化方法（cosine）。
- API 路由：`api/routes/retrieval.py`（`/api/retrieval/test`），统一 envelope `{code,data}`。
- 手工验证脚本（非 pytest）：`EviQAsys/backend/tests/manual/test_m3_embedding_and_retrieval.py`。
- 环境配置与文档：新增嵌入相关 env 配置项与 README 片段。

## 参考与约束
- 路线图要求（docs/en/Develop_Road_Map.md / M3）。
- 嵌入接口示例：`dependency/multiModalEmbedding/demo_jina_local_embedding.py`（vLLM 提供 `/v1/embeddings`，模型名示例：`jinaembeddingv4`）。
- OceanBase 已包含 `elements.vec_embedding VECTOR({VECTOR_DIM})` 字段，默认 `VECTOR_DIM` 由环境变量控制。
- 测试遵循 AGENTS.md：仅手工脚本，使用真实数据，不引入 pytest。

## 实施步骤（执行顺序）
1) 环境与配置
- 在 `EviQAsys/backend/app/env_setting.py` 增加嵌入相关配置：
  - `EMBEDDING_ENDPOINT`（默认 `http://localhost:7701/v1/embeddings`）
  - `EMBEDDING_MODEL`（默认 `jinaembeddingv4`）
  - `EMBEDDING_TIMEOUT_S`（默认 60）/ `EMBEDDING_MAX_RETRIES`（默认 1-3）
- 校验/调整 `VECTOR_DIM` 使之与模型输出维度一致（若不一致，启动时告警并拒绝写入）。

2) 嵌入服务封装（services/embedding/embedding_service.py）
- 封装 `embed_message(content_blocks: list[dict]) -> list[float]`，请求体遵循 demo：
  - 文本：`[{"type":"text","text":...}]`
  - 文本+图：追加 `{"type":"image_url","image_url":{"url":"data:image/png;base64,..."}}`
- 暴露方法：
  - `embed_text(text: str) -> list[float]`
  - `embed_text_image(text: str, image_b64: str|None) -> list[float]`
  - `batch_embed_elements(elements: list[dict]) -> dict[element_id, vector]`
- 内置超时、重试、简单日志；失败返回可识别错误并由调用方决定跳过/重试。

3) 元素选取与多模态策略
- text/header：仅用 `text_content` 生成向量。
- image/table/equation：联合 `text_content(含caption)` + `image_base64` 生成单一向量；若图片缺失则退化为文本-only。

4) 仓储扩展（repositories）
- `ElementsRepository`：
  - 新增 `update_element(element_id, vec_embedding=...)` 的批量写入支持（沿用现有 `update_element` / `batch_insert` 风格）。
  - 新增简化 TopK 检索：`topk_by_collection(collection_id, query_vec, k)`：
    - 方案A（优先）：利用 OceanBase 向量函数（若可用）直接在 SQL 端计算 cosine 并排序。
    - 方案B（兜底）：限定集合范围（如某 collection 或 doc）拉取 `vec_embedding` 到后端，用 Python 计算 cosine，再返回 TopK（注意分页与内存）。

5) 检索编排（services/retrieval/retriever.py）
- `embed_query(text) -> qvec`；
- `retrieve_topk(collection_id, query_text, k)`：调用仓储相似度查询，返回：`{element_id, doc_id, page_no, bbox, elem_type, score}`。

6) API 路由（api/routes/retrieval.py）
- `GET /api/retrieval/test?collection_id=&query=&top_k=`
  - 返回 `{"code":"OK","data":[{doc_id,page_no,bbox,elem_type,score}]}`
  - 仅用于验证通路与数据形态，不做复杂过滤/分桶。

7) 批处理触发（脚本优先）
- 手工脚本：扫描 `elements` 中 `vec_embedding IS NULL` 的记录，按批次调用 `embedding_service` 写回。
- 可选：补充 `POST /api/collections/{id}/embed` 作后续触发口（M3 不强制）。

8) 数据一致性与监控
- 写入前校验 `len(embedding) == VECTOR_DIM`；不一致直接报错并跳过该条。
- 记录批量统计（总数、成功/失败、平均/TP99 延迟、失败原因 TopN）。

9) 文档与配置更新
- 在 `docs/en` 与 `docs/zh` 对应章节补充嵌入与检索的配置项与调用链说明。

## 手工验证（建议流程）
1. 已完成 M2，至少有 1 个文档入库并生成 `elements` 记录。
2. 运行手工脚本 `python EviQAsys/backend/tests/manual/test_m3_embedding_and_retrieval.py`：
   - 对 `vec_embedding IS NULL` 的元素批量向量化；
   - 随机挑选一个查询（或由用户输入）在指定 `collection_id` 上检索 TopK；
   - 打印：元素总数、已写入向量数、向量维度、检索用时、TopK 示例（doc_id/page_no/elem_type/score/bbox）。
3. 启动后端，调用 `GET /api/retrieval/test` 复现同样的结果形态。

## 风险与回退
- 维度不匹配：启动时即比对并报错；必要时回退到关闭写向量，仅跑检索脚本校验。
- 吞吐与时延：先用小批量/串行保证正确性，必要时再引入并发与批量请求。
- OceanBase 向量函数能力不明确：优先落地 B 方案；A 方案待确认后切换。
- 图片缺失或过大：统一退化为文本-only；限制单条请求最大图片大小（base64 长度阈值）。

## 时间预估（工作量粗估）
- 封装与脚本：0.5-1 天
- 仓储与 API：0.5 天
- 手工验证与文档：0.5 天
- 预留问题澄清与环境联调：0.5 天

