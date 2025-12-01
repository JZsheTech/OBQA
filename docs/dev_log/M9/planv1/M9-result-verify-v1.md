# M9 阶段结果与验证记录

## 已完成内容
- **数据层**：新增 `chunks` / `page_text_chunks` 表及索引，elements 保留渲染字段；新增 chunk/page chunk 仓储与配置项（最小字符、最大窗口、跳过模式、页级 topK 开关）。
- **索引链路**：`ChunkBuilder` 按 section 无 overlap 聚合文本，image/table 单元素单 chunk；`DocumentIndexer` 重建 chunk/page_chunk 并嵌入；ingestor 写入 `text_content=raw_text_content`，不再生成 header summary。
- **检索与 QA**：Retriever 以 chunk 为主入口，支持页级过滤与 chunk→element 展开；QA 侧用 `[Elem#<id>] raw_text` 组装上下文，图片证据仍可选 VQA。
- **API/文档**：检索接口返回 chunk 结果并开放页级参数；数据模型与设计文档同步 chunk/page_chunk 改动；Evidence 输出/提示文案带 `[Elem#id]` 前缀。

## 静态校验
- `/data2/jproject/condaEnvData2/systool/bin/python -m compileall EviQAsys/backend/app`：通过，所有改动文件可编译。

## 手工验证建议（使用真实解析文档）
1. **索引重建与入库**
   - 通过上传或调用 `DocumentIngestor` + `DocumentIndexer.embed_document(collection_id, doc_id)`，核对 `chunks/page_text_chunks` 行数、`elem_ids` 去重、`chunk_type` 分布及 `page_start/page_end`。
   - 随机抽取 image/table chunk，确认向量已写入、caption/markdown 保持。
2. **检索链路**
   - 调用 `GET /api/retrieval/test`，分别在 `search_mode=vector/hybrid/fulltext`、开启/关闭页级过滤下比对命中页与 chunk_type 过滤效果。
   - 检查返回的 `elem_ids/level_nav/page_start/page_end` 是否与 DB 中 chunk 定位一致。
3. **QA 回答与锚点**
   - 建立 chat 后提问，观察回答上下文是否按 chunk 顺序生成 `[Elem#id]` 锚点，`turn2element` 记录与答案中的元素一致。
   - 若开启图像 VQA，确认 Vision 摘要被拼入 image evidence。
