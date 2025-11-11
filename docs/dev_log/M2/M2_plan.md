# M2 阶段执行计划：文档上传 → MinerU 解析 → 规范化入库

依据 docs/en/Develop_Road_Map.md 的 M2 要求，并结合 docs/dev_log/M2/minerU_parse_func.md 的处理流水线，形成如下执行计划。M2 的目标是：前端上传一个 PDF，后端同步调用 MinerU 解析，完成“标题层级修复 + 统一元素化”，并将结果写入 documents/elements，前端可在“文档列表”看到该 PDF。

## 1. 目标与 DoD
- 目标：完成同步上传与解析入库的最小闭环（不含向量与检索）。
- DoD：
  - 前端可上传单个 PDF 至某 collection；
  - 后端同步调用 MinerU 得到 `md_text + content_list`；
  - 执行“标题层级修复 + 统一元素化”，生成统一文本视图：`text_content / header_name / level_nav / page_no / bbox_json / text_caption / image_base64 / order`；
  - 写入 `documents` 与 `elements`；
  - 前端“Document List”中可看到新文档记录。

## 2. 范围与不包含
- 本阶段包含：上传接口、MinerU 解析集成、元素规范化、批量入库、最小前端上传视图与列表视图。
- 本阶段不包含：Embedding、向量检索、QA 流程、PDF 高亮跳转（留待 M3+M4+M5）。

## 3. 架构与代码落点
- 后端目录：`EviQAsys/backend/app`
  - `api`：新增上传路由 `POST /api/collections/{id}/documents`（multipart）。
  - `services/integrations`：`mineru_adapter.py`（封装 MinerU，同步返回 `md_text, content_list`）。
  - `services/retrieval`（或 `services/parser`，按现有结构选一个子包）：
    - `header_processor.py`：`preprocess_header(content_list)`
    - `summarizer.py`：`tfidf_summary(text)`（轻量摘要，仅用于 header）
    - `unifier.py`：`normalize_element(item) -> dict`
  - `services/ingestion`：`document_ingestor.py`（编排：保存文件→调用 MinerU→规范化→批入库）
  - `repositories`：沿用 M1 已有 `documents_repo.py`、`elements_repo.py`（补充批量插入函数）。
  - `schemas`：上传请求/响应 DTO；elements/document 的内部模型（尽量贴合 Data_Model）。

## 4. 数据与字段规范（统一文本视图）
- 核心类型与映射（参考 minerU_parse_func.md 与 Data_Model）：
  - `elem_type`：`text|header|image|table|equation`
  - `text_content`：
    - text：`[level_nav] [header_name] + 原文文本`
    - header：`[level_nav] [header_name] + section_summary`
    - image：`[level_nav] [header_name] + caption`
    - table：`[level_nav] [header_name] + caption + 表格文本`
    - equation：`[level_nav] [header_name] + latex/text`
  - `header_name`、`header_level`、`level_nav`：由 `preprocess_header` 计算与补全。
  - `text_caption`：来自 MinerU caption 原文。
  - `image_base64`：来自 MinerU 图像 base64（原样或去除 data URI 前缀）。
  - `bbox_json`：MinerU 原始 bbox 数组 JSON 序列化。
  - `page_no`：PDF 页码；`order`：在 `content_list` 中的顺序索引（从 0 起）。
- M2 不写入 `vec_embedding`（Embedding 留到 M3）。

## 5. 后端实现步骤
1) API 设计与骨架
   - 路由：`POST /api/collections/{id}/documents`（multipart，字段：`file`）。
   - 返回：`{ doc_id, filename, size, status: "stored" }`。
   - 存储上传文件到本地持久目录（需确认路径与配额，见“启动前确认”）。

2) Ingest 编排服务 `document_ingestor.py`
   - 输入：`collection_id`, `file_path`。
   - 流程：
     a. `documents_repo.create()` 插入文档元数据（name, size, mime, path, collection_id）。
     b. `mineru_adapter.parse(pdf_path) -> (md_text, content_list)`。
     c. `header_processor.preprocess_header(content_list)` 计算 `header_name/level_nav/header_level/order_start/order_end`。
     d. 对 `header` 元素收集区间文本，`summarizer.tfidf_summary()` 生成 `section_summary`，合并入该 header 的 `text_content`。
     e. `unifier.normalize_element()` 逐条产出统一元素字典，补齐 `doc_id/order/page_no/bbox_json/text_caption/image_base64` 等字段。
     f. `elements_repo.batch_insert(elements)` 批量入库（建议 batch size=32）。
     g. `documents_repo.update_parsed(doc_id, md_text, elem_count)`。

3) MinerU 集成 `mineru_adapter.py`
   - 以 `dependency/minerUparseDemo/parse_pdf_minerU.py` 为样例；
   - 提供两种模式（择一/可切换）：
     - 本地 Python 调用（import 或子进程）
     - HTTP 本地服务调用（如 MinerU 提供 REST）
   - 输出统一：`md_text: str | None`, `content_list: List[dict]`。

4) 仓储层补全
   - `documents_repo.py`：`create() / update_parsed()`；
   - `elements_repo.py`：`batch_insert(rows: List[dict])`，校验必填字段与合法类型。

5) 错误处理与幂等
   - 上传失败、解析失败、入库失败分别捕获并回滚文档状态；
   - 同一文件重复上传策略：按 `collection_id + filename + size` 做防重或直接允许重复（需确认）。

## 6. 前端最小实现
- `POST /api/collections/{id}/documents` 的上传表单（仅单文件）；
- “Document List” 视图：列出 `documents` 基本信息（name, size, created_at, element_count）。

## 7. 运行与配置
- Conda 环境：`quest`（后端）与 `jzMinerUVllm`（MinerU）。
- 环境变量：
  - `MINERU_MODE=local|http`，`MINERU_ENDPOINT`（http 模式），`VECTOR_DIM`（M2 可忽略）、`BATCH_SIZE=32`；
  - `UPLOAD_DIR`、`MAX_UPLOAD_MB`、`MINERU_TIMEOUT_S`。
- 启动命令：`uvicorn EviQAsys.backend.app.main:app --app-dir EviQAsys/backend --reload`。

## 8. 手工验证（符合本仓库测试约束）
- 不使用 pytest；提供独立脚本 `tests/manual/test_m2_ingest.py`（仅手动运行）：
  - 读取 `sample_data/` 下真实 PDF 路径；
  - 直接调用后端 ingest 服务主函数（不写入生产库副作用之外的数据）；
  - 打印：解析到的元素数量、各类型计数、示例元素的 `level_nav/header_name/page_no/bbox_json`；
  - 人工检查控制台输出，确认逻辑一致性。

## 9. 里程碑交付清单
- 后端：上传 API、ingest 编排、MinerU 适配器、处理器与统一化模块、仓储批量入库；
- 前端：最小上传 + 文档列表；
- 文档：更新 `docs/en/Develop_Road_Map.md`（已对齐）、记录 `docs/dev_log/M2` 实施结果；
- 手工验证脚本与运行说明。
