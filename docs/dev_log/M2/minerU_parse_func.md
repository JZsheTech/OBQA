

# 📘 MinerU 文档处理与入库模块设计（独立系统版）

## 0. 目标与范围

本模块负责从 PDF 文件中解析出结构化的文档元素，生成统一多模态向量，并将结果批量入库至数据库表 **`elements`**。
目标流程为：

```
PDF → MinerU解析 → Element结构化拼装 → Jina v4 向量生成 → 批量入库(elements)
```

不包含：检索、排序、前端展示或API兼容逻辑。

---

## 1. 输入与输出定义

### 输入

* **源文件**：PDF 文件路径或字节流
* **外部依赖**：

  * MinerU 文档解析模块 (`parse_pdf_mineru_parallel.py`)
  * Jina Embeddings v4（多模态统一向量）
  * TF-IDF 摘要生成器 (`tfidf_summary`)

### 输出

数据库表 `elements` 中的一组记录，每条记录代表一个解析出的文档元素。

---

## 2. 处理流水线（落库前步骤）

### 2.1 MinerU 解析

* 输入：PDF 文件
* 输出：

  * `md_text`：全文 Markdown 文本（可选）
  * `content_list`：元素序列，包含：

    * `elem_type` (`text` / `header` / `image` / `table` / `equation`)
    * `page_no`, `bbox`, `caption`, `text`, `image_base64` 等

---

### 2.2 标题层级修复 `preprocess_header()`

为确保标题层级正确、层级关系可追踪，对解析结果执行以下处理：

* 修复编号跳级（如 `1`, `1.1`, `2.1.2`）
* 对每个元素增加：

  * `header_name`：最近上级标题文本
  * `header_level`：层级深度（整数）
  * `level_nav`：完整章节路径（例如 `1. Introduction > 1.1 GNN > 1.1.1 Message Passing`）
* 对 `header` 类型元素，计算所属章节范围：

  * `order_start`：章节起始元素序号
  * `order_end`：章节结束元素序号（闭区间或开区间由实现决定）

---

### 2.3 章节摘要生成（轻量）

* 对每个 `header` 元素，聚合 `[order_start, order_end]`(2边都是闭区间) 范围内所有文本化内容（`text`、`table`、`equation`、`caption`）
* 用 `tfidf_summary` 生成 `section_summary`
* 将摘要合并入该 `header` 元素的 `text_content`

---

### 2.4 Element 统一化拼装规则

在入库前对每个元素执行标准化拼装：

| 元素类型       | 拼装逻辑（`text_content`）                          |
| ---------- | --------------------------------------------- |
| `text`     | `[level_nav] [header_name] + 原文文本`            |
| `header`   | `[level_nav] [header_name] + section_summary` |
| `image`    | `[level_nav] [header_name] + caption`         |
| `table`    | `[level_nav] [header_name] + caption + 表格文本`  |
| `equation` | `[level_nav] [header_name] + latex/text`      |

其他字段映射规则：

| 字段             | 来源                             |
| -------------- | ------------------------------ |
| `text_caption` | MinerU caption 原文              |
| `image_base64` | MinerU 输出的图像数据（可含 data URI 前缀） |
| `bbox_json`    | 原始 bbox 坐标数组 JSON              |
| `page_no`      | PDF 页号                         |
| `order`        | 在 `content_list` 中的顺序索引（从 0 起） |

---

### 2.5 向量生成（Jina v4）

统一多模态嵌入策略：

| 元素类型     | 嵌入输入                         |
| -------- | ---------------------------- |
| 文本元素     | `text_content`               |
| 图片元素     | `image_base64`               |
| 图文混合（可选） | messages = [{text}, {image}] |

结果字段：

* `vec_embedding`：统一多模态向量（VECTOR 类型）
* 维度通过环境变量 `VECTOR_DIM` 配置

---

### 2.6 批量入库策略

* 建议批量写入（batch size = 32）
* 每批执行 `INSERT ... ON CONFLICT (id) DO UPDATE`
* 入库前校验：

  * 所有向量维度一致 (`VECTOR_DIM`)
  * 必填字段非空（`doc_id`, `elem_type`, `order`, `text_content` 或 `image_base64`）
* 为简化起见，文档入库后不允许更新其中的element。

---

## 3. 数据表结构（目标数据库）

### 3.1 `elements`
表格schema定义见docs/en/Data_Model.md

> **注意**
>
> * `VECTOR_DIM` 可在环境变量或初始化脚本中设定。
> * 本模块仅负责生成和写入向量，不创建额外的 KNN 索引。

---

## 4. 模块化实现建议

| 模块                    | 功能                         | 核心函数                                                |
| --------------------- | -------------------------- | --------------------------------------------------- |
| `mineru_adapter.py`   | 调用 MinerU 并返回 content_list | `mineru_parse(pdf_path) -> (md_text, content_list)` |
| `header_processor.py` | 计算标题层级与章节范围                | `preprocess_header(content_list)`                   |
| `summerizer.py`       | 生成章节摘要                     | `tfidf_summary(text) -> str`                        |
| `unifier.py`          | 元素拼装与命名规范化                 | `normalize_element(item) -> dict`                   |
| `embedder_jina_v4.py` | 向量生成                       | `embed_unified(text, image_b64) -> vector`          |
| `dao_elements.py`     | 数据库写入                      | `batch_upsert_elements(rows)`                       |

---

## 5. 最小可行示例代码

```python
def ingest_pdf(pdf_path: str, doc_id: int):
    # Step 1: MinerU 解析
    md_text, content_list = mineru_parse(pdf_path)

    # Step 2: 标题层级修复
    elements = preprocess_header(content_list)

    # Step 3: 摘要生成（仅 header）
    for elem in elements:
        if elem["elem_type"] == "header":
            section_text = collect_text_in_range(elements, elem["order_start"], elem["order_end"])
            elem["text_content"] = tfidf_summary(section_text)

    # Step 4: 统一化拼装
    unified_rows = []
    for i, e in enumerate(elements):
        row = normalize_element(e)
        row.update({
            "doc_id": doc_id,
            "order": i,
            "created_at": datetime.now(),
        })
        unified_rows.append(row)

    # Step 5: 统一向量生成
    for r in unified_rows:
        r["vec_embedding"] = embed_unified(r["text_content"], r["image_base64"])

    # Step 6: 批量入库
    batch_upsert_elements(unified_rows)
```

---

## 6. 注意事项与一致性要求

| 项                | 说明                                                                        |
| ---------------- | ------------------------------------------------------------------------- |
| **Base64 前缀**    | 若以 `data:image/...;base64,` 开头，嵌入前可调用 `_strip_data_uri()` 去除前缀。           |
| **字段映射**         | 原文中的 `elem_order`→`order`；`emb_vec`→`vec_embedding`；`page_idx`→`page_no`。 |
| **章节范围**         | 原文的 `order_start`、`order_end` 保留；类型改为 `VARCHAR`（与新结构保持一致）。                |
| **header_level** | 新增字段，源自标题层级计算。                                                            |
| **索引与性能**        | 不启用向量索引；后续检索模块按需在应用层实现。                                                   |
| **解析清洗**        | MinerU 返回的文本若仅由 `#` 与空白组成（常见于代码注释占位行），入库前会被丢弃，避免污染 elements。          |

---

✅ **最终迁移后的主干流程（简化图）**

```
PDF
 ↓
MinerU parse
 ↓
content_list → preprocess_header → section_summary(tfidf)
 ↓
normalize_element → embed_unified(Jina v4)
 ↓
batch_upsert → elements表
```

# 可参考的已有代码

docs/dev_log/M2/ref_code

# 参考的mineru解析出的数据格式：
docs/dev_log/M2/ref_data_format
