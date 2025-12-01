## 三级分块架构总览

- **Element 级**：MinerU 解析 PDF，`DocumentIngestor` 预处理 header（`preprocess_headers`）、`normalize_element`，并写入 elements 表。`level_nav` 按章节层级保存，`text_content` 与 `raw_text_content` 保持一致，不做摘要。
- **Chunk 级**：`ChunkBuilder.build_chunks` 在同一 `level_nav` 内顺序合并文本元素，遵守 `MIN_CHARACTOR_CHUNK_SIZE` / `MAX_CHARACTOR_CHUNK_SIZE` 与 `CHUNK_SKIP_PATTERNS`，不做 overlap；image/table 元素单独成块。
- **Page 级**：`ChunkBuilder.build_page_chunks` 按页聚合文本（忽略 image/table），用于页级检索（由 `ENABLE_PAGE_TEXT_CHUNKS` 控制）。

## Chunk 构造与阈值规则（文本）

- 按元素顺序遍历，同一 `level_nav` 连续聚合；切换章节立刻落库当前块。
- `MAX_CHARACTOR_CHUNK_SIZE`：顺序累加文本长度，首次超过上限时触发截断逻辑。
- `MIN_CHARACTOR_CHUNK_SIZE`：落库前检查，若最终文本块字符数低于该值则直接丢弃并计数日志（`Dropped %s text chunks below MIN_CHARACTOR_CHUNK_SIZE=...`），避免极短噪声进入检索。
- 单元素超长（长度 > MAX）：若缓冲区内已有文本但仍未达最小值，会将该超长元素与缓冲一起落为同一块，避免短标题被孤立；否则单元素独立成块。
- 累加后超过上限但当前缓冲未达最小值的情况（如“1.1 GNN”短标题 + 中等长度正文导致总长 > MAX）：会把该文本元素继续加入缓冲并立即落库，生成一个可能超过 `MAX_CHARACTOR_CHUNK_SIZE` 的块，确保小标题不被单独丢弃。

## Chunk 构造与阈值规则（多模态）

- `elem_type` 为 image/table 时不参与文本聚合，直接单元素成块；不受 `MIN_CHARACTOR_CHUNK_SIZE` 过滤影响。
- 多模态块的文本由原始内容 + caption 去重组合，依旧记录 `page_start/page_end` 与 `elem_ids`。

## Page Chunk 规则

- 按页号聚合文本元素（忽略 image/table），简单拼接为页级文本块。
- 不施加最小/最大字符限制，空文本会被跳过。

## 关键配置

- `MIN_CHARACTOR_CHUNK_SIZE`：文本块最小字符数，下限过滤开关。
- `MAX_CHARACTOR_CHUNK_SIZE`：文本块目标上限，控制聚合窗口。
- `CHUNK_SKIP_PATTERNS`：正则跳过无意义文本（控制字符、纯分隔符等）。
- `ENABLE_PAGE_TEXT_CHUNKS`：是否生成页级块。

## 参考实现位置

- 元素入库与预处理：`EviQAsys/backend/app/services/ingestion/document_ingestor.py`
- 文本/多模态 chunk 构建与丢弃规则：`EviQAsys/backend/app/services/index/chunk_builder.py`
- 页面级 chunk 构建：`EviQAsys/backend/app/services/index/chunk_builder.py` 中 `build_page_chunks`
