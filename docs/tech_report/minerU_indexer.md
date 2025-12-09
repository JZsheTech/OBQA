# MinerU 解析元素使用报告与索引建立指南（自包含版）

> 目标：独立说明 MinerU 解析、元素入库、索引/向量构建与前端高亮要点，迁移到其他系统时仅需本文件和源码实现。关键实现文件：`EviQAsys/backend/app/services/ingestion/document_ingestor.py`、`.../integrations/mineru_adapter.py`、`.../parser/header_processor.py`、`.../parser/unifier.py`、`.../index/chunk_builder.py`、`.../index/document_indexer.py`。

## 1. MinerU HTTP 接口与返回

- 调用：multipart/form-data POST（字段名 `files`），上传 PDF 字节。
- 主要参数（与 MinerU API 对齐）：
  - `lang_list`: 语言列表，默认 `["en"]`。
  - `backend`: `pipeline`（默认）或 `vllm-async-engine`。
  - `parse_method=auto`，`formula_enable=true`，`table_enable=true`。
  - `return_md=true`，`return_content_list=true`，`return_images=true`。
  - `return_middle_json=false`，`return_model_output=false`。
  - `response_format_zip=false`，`start_page_id=0`，`end_page_id=99999`。
- 返回结构：`{"results": {<pdf_stem>: {"md_content": str|None, "content_list": list|json str, "images": dict}}}`。
- content_list 常见字段：
  - `type`: `text` / `image` / `table` / `equation` / `header` / `discarded`
  - `text`, `text_level`（标题提示），`table_body`（Markdown），`image_caption` / `table_caption`（列表）
  - `bbox` 或 `bbox_json`: `[x0, y0, x1, y1]`
  - `page_idx`(0 基) 或 `page_no`(1 基)，`img_path` 对应 `images` 的键
- 坐标系：MinerU bbox 使用 0~1000 基准，点序为左上 / 右下。渲染时按页面实际宽高等比缩放；若页旋转，需按渲染器旋转信息校正；若发现 y 轴原点差异，可用 `y' = H - y` 方式翻转。

## 2. 数据模型（表结构与字段语义）

- `documents`：
  - `id`, `collection_id`, `title`（首个有效 header，缺失则文件名 stem），`md_text`（全文 Markdown），`abstract`（见 3.5），`file_name`/`file_path`/`file_sha256`/`file_size_bytes`
  - `num_pages`（元素最大页），`element_count`，`meta_info`（JSON，可空）
- `elements`：
  - `id`, `doc_id`, `order`（content_list 顺序，0 起）
  - `elem_type`: `text`/`header`/`image`/`table`/`equation`
  - `header_name`（最近标题或 `root`）、`header_level`、`level_nav`（章节路径，空则 `root`）
  - `text_content` 与 `raw_text_content`（当前相同，等于 MinerU 原文聚合，不加前缀/上下文）
  - `text_caption`（图表 caption 聚合），`image_base64`（去掉 data URI 前缀）
  - `bbox_json`（MinerU 坐标原样 JSON），`page_no`（1 基；若只有 `page_idx` 则 +1）
  - `order_start`/`order_end`（header 对应章节范围，字符串存储）
- `chunks`（主索引）：
  - `id`, `doc_id`, `collection_id`, `order`, `level_nav`, `chunk_type`(`text`/`image`/`table`)
  - `chunk_text_main`（合并文本或图表说明），`elem_ids`（JSON, 顺序去重），`page_start`/`page_end`，`vec_embedding`
- `page_text_chunks`（可选页级索引）：
  - `id`, `doc_id`, `collection_id`, `chunk_text_main`, `elem_ids`, `page_no`, `chunk_type=text`, `vec_embedding`

## 3. 入库流水线（DocumentIngestor）

1) 上传与去重  
   - 文件存入 `UPLOAD_DIR/<collection_id>/`，计算 `sha256`、大小、原始名。  
   - 去重键：`collection_id + file_name + file_sha256`，命中即拒绝。

2) 调用 MinerU  
   - `MinerUAdapter.parse` 上传 PDF，返回 `md_text`、`content_list`、`images`（字典键为图片文件名）。

3) 噪声过滤  
   - 丢弃 `type` 不在 `{text,image,table,equation}` 的元素。  
   - 丢弃文本仅由 `#`/空白组成的占位项。若过滤后为空则报错。

4) 标题/层级修复 `preprocess_headers`  
   - 跳过 MinerU 的 `header`/`discarded`。  
   - 识别标题：`type=="text"` 且 `text_level` 存在，合并数字或字母编号；推断 `header_level`。  
   - 生成：`elem_type`、`header_name`、`header_level`、`level_nav`、`order`、`order_start`、`order_end`。  
   - 首页相邻同级标题会尝试合并为论文主标题（用于文档标题回填）。

5) 文档标题与摘要  
   - 标题：首个有效 header（非 `root`）；否则文件名 stem。  
   - 摘要：先找标题为 “Abstract” 的 header，取其后首个非 header 的文本；若未命中，扫描前 2 页正文，匹配 `^\s*abstract[:：\-–—\.]+\s*(.+)`。

6) 元素规范化 `normalize_element`  
   - `elem_type` 小写，`header_name`/`level_nav` 为空则用 `root`。  
   - `raw_text_content` / `text_content`：  
     - header → 清洗标题文本；text → MinerU `text`；image → caption 汇总；table → caption + `table_body`；equation → `text` 或 `latex`。  
   - `text_caption`：image/table caption 聚合；`image_base64`：按 `img_path` 在 `images` 中取值并去除 data URI 前缀。  
   - `bbox_json`：`bbox`/`bbox_json` 原样 JSON；`page_no`：优先 `page_no`，否则 `page_idx+1`。  
   - `order_start`/`order_end`：字符串保存。入库前写入 `doc_id`、`order`，统计 `num_pages` 与 `element_count`。

7) 入库  
   - 事务内批量插入 `elements`，更新 `documents` 的 `md_text`、`num_pages`、`element_count`、`abstract`、`title`。

## 4. 索引与向量构建（DocumentIndexer）

1) Chunk 构建 `ChunkBuilder.build_chunks`  
   - 按 `order` 排序后遍历；`level_nav` 变化则结束当前段。  
   - 文本窗口：聚合同一 `level_nav` 的文本/公式元素，阈值  
     - `MIN_CHARACTOR_CHUNK_SIZE`（默认 256）  
     - `MAX_CHARACTOR_CHUNK_SIZE`（默认 3200）  
     - `CHUNK_SKIP_PATTERNS` 过滤控制字符等。  
   - 超长元素 > MAX：若缓冲未达最小值则并入后落块，否则单元素成块。  
   - 超过上限但缓冲未达最小值：继续累加并立刻落块，允许略超长以避免短标题被丢弃。  
   - 低于最小值的文本块会被丢弃并日志记录。  
   - 多模态：`image/table` 不参与文本聚合，单元素单 chunk；`chunk_text_main` 为去重后的 `raw_text_content`/`text_caption` 组合；`page_start/page_end` 取元素页号，`elem_ids` 顺序去重。

2) 页级 Chunk（可选）  
   - `ENABLE_PAGE_TEXT_CHUNKS=true` 时，按 `page_no` 聚合文本/公式元素为页级文本块，不设长短阈值。

3) 嵌入 `EmbeddingService`  
   - 入口 `DocumentIndexer.embed_document`：重建 chunks → 嵌入 → 写向量。  
   - 文本 chunk：`embed_text(chunk_text_main)`；图表 chunk：`embed_text_image(text, image_base64)`（两者皆空跳过）；页级 chunk：文本嵌入。  
   - 维度校验：返回长度必须等于 `VECTOR_DIM`，否则抛异常。  
   - 嵌入结果写入 `chunks.vec_embedding`、`page_text_chunks.vec_embedding`。

## 5. 坐标与前端高亮约定

- 存储：`bbox_json` 为 MinerU 原始 `[x0,y0,x1,y1]`，基于 0~1000 左上原点。  
- 渲染：按 PDF 页面宽高等比缩放；若渲染器以左下为原点需做 y 轴翻转；若页面有旋转按实际旋转角度调整。  
- 高亮关联：使用 `doc_id + page_no + bbox`，前端将 `[Elem#id]` 替换成 `[Evidence#no]` 时需保留 `element_id` 以定位。

## 6. 环境与配置（默认值，可通过 env 或 `config.yaml` 设置）

- MinerU：`MINERU_MODE=http`，`MINERU_ENDPOINT=http://127.0.0.1:18543/file_parse`，`MINERU_BACKEND=pipeline`，`MINERU_LANG_LIST=en`，`MINERU_TIMEOUT_S=600`。  
- 上传：`UPLOAD_DIR=/tmp/obqa_uploads`，`MAX_UPLOAD_MB=200`。  
- Chunk：`MIN_CHARACTOR_CHUNK_SIZE=256`，`MAX_CHARACTOR_CHUNK_SIZE=3200`，`CHUNK_SKIP_PATTERNS=(r"^\\s*$", r"^[\\u0000-\\u001f\\u007f]+$")`，`ENABLE_PAGE_TEXT_CHUNKS=true/false`。  
- 向量：`EMBEDDING_ENDPOINT=http://localhost:7701/v1/embeddings`（OpenAI 兼容），`EMBEDDING_MODEL=jinaembeddingv4`，`VECTOR_DIM=2048`，`EMBEDDING_TIMEOUT_S=60`，`EMBEDDING_MAX_RETRIES=1`。  
- 其他常用：`BATCH_SIZE`(入库/向量批大小，默认 32)。

## 7. 迁移落地 Checklist

1. 部署 MinerU HTTP 服务（`mineru-api --host 0.0.0.0 --port 18543`），确认与上面参数一致。  
2. 复用或实现 `MinerUAdapter.parse`：构造表单请求，解析 `md_content`/`content_list`/`images`，支持字符串/列表形式的 content_list。  
3. 搭建相同的数据表结构；保证 `bbox_json/page_no/level_nav` 等字段语义一致。  
4. 复刻入库链路：去重 → 噪声过滤 → `preprocess_headers` → 文档标题/摘要提取 → `normalize_element` → 批量写 `elements`、更新 `documents`。  
5. 配置并运行索引：`ChunkBuilder` 规则、页级 chunk 开关、`DocumentIndexer` 嵌入；校验向量维度。  
6. 用真实 MinerU 输出（如 `sample_data/converted_doc/demo1`）或新 PDF 手动跑一遍 ingest → chunk → embed，核对元素数、页数、bbox 缩放与高亮位置。  
7. 前端/调用方依据 `element_id` 渲染证据，使用 `doc_id/page_no/bbox` 高亮；避免自行生成 evidence 编号而脱离后端映射。
