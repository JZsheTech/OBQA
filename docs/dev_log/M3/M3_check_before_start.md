# M3 开发前需确认的问题清单（澄清点）

为确保按路线图高效推进，请协助确认以下不确定项：

## 嵌入服务与模型
- 服务地址与端口：是否统一为 `http://localhost:7701/v1/embeddings`？是否存在代理/网关前缀？
- 模型名称：是否固定为 `jinaembeddingv4`？是否需要多模型可切换？
- 认证方式：当前是否无需鉴权？若需要，请提供 token/headers 规范。
- 维度确认：`jinaembeddingv4` 实际输出维度是多少？需与 `VECTOR_DIM` 严格一致（默认 64 可能不符）。

## 多模态策略与元素范围
- 参与嵌入的元素类型：是否包含 `header`？是否对 `text` 与 `header` 统一处理？
- 对 `image/table/equation`：是否强制“文本+图片联合嵌入”？图片缺失时是否退化为文本-only？
- 文本来源：对图片/表格，是否使用 `text_caption` 作为 `text_content` 参与联合嵌入？

## OceanBase 与相似度计算
- 是否可用 OceanBase 的向量相似度/运算函数（cosine/dot）？如可用，请提供函数名/示例。
- 若暂不可用，是否接受后端从限定集合（如按 collection 过滤）拉取向量在 Python 中计算 cosine 并返回 TopK？
- TopK 默认值与是否需要相似度阈值（如 `score >= 0.3`）？

## 触发方式与批处理
- M3 期望的最小触发路径是脚本优先还是提供 API 触发（或两者都要）？
- 批处理参数：每批大小（建议 16-64）、并发度、超时（建议 60s）、最大重试次数（建议 1-3）。
- 失败策略：单条失败是否跳过继续？是否需要失败清单导出/重试脚本？

## `/api/retrieval/test` 输出形态
- 返回字段是否固定为 `{doc_id, page_no, bbox, elem_type, score}`？是否需要 `element_id`、`header_name` 以便前端调试？
- 结果是否必须按 `score` 降序？是否需要返回 `k` 与耗时统计？
- 查询范围是否限定在 `collection_id`（必选）？是否允许按 `doc_id` 再次过滤？

## 资源与运维
- vLLM + Jina Embeddings v4 的部署是否由运维同学统一提供？端口/版本是否已冻结？
- 资源限制（CPU/GPU/内存）与图片 base64 的大小上限（是否需要 512KB-1MB 限制）？
- 是否需要在 `.env` 或系统 env 中新增/暴露：`EMBEDDING_ENDPOINT`、`EMBEDDING_MODEL`、`EMBEDDING_TIMEOUT_S`、`EMBEDDING_MAX_RETRIES`？

## 测试与样本
- 手工测试所用的 PDF 样本路径与最小规模（建议 ≥1 份包含公式/表格/图片的文档，≥1 份纯文本文档）。
- 验收口径：是否以“已写入向量数量、维度一致性、TopK 返回结构与可读性”为主要验收指标？

## 其它
- 是否需要在 M3 暂时跳过“去重与类型分桶”的复杂逻辑，仅保留接口预留点？
- 前端是否需要在 M3 提供最小的调试视图（仅打印返回 JSON）？若需要，请给出最小字段集合。

参考实现与示例：`dependency/multiModalEmbedding/demo_jina_local_embedding.py`

