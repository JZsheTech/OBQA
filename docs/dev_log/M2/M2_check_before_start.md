# M2 启动前需确认的问题清单（请开发者答复）

为降低返工风险，以下关键点在 M2 实施前需明确：

## 集成与运行方式
- MinerU 集成模式确认：本地 Python 调用 还是 本地 HTTP 服务？若为 HTTP，请提供 `MINERU_ENDPOINT` 与鉴权方式；若为本地调用，请确认可直接 import 的模块路径或需以子进程执行的脚本入口。
- MinerU 返回结构是否与 `dependency/minerUparseDemo/parse_pdf_minerU.py` 一致？`md_text` 是否稳定可用？`content_list` 的字段命名是否固定（`elem_type/page_no/bbox/caption/text/image_base64`）。
- 是否要求对上传处理全程“同步阻塞”？若解析超过 `MINERU_TIMEOUT_S`，期望的超时/回滚策略是什么？

## 存储与数据模型
- 上传 PDF 的落盘目录与命名策略？建议提供 `UPLOAD_DIR`，是否需要以 `collection_id/` 分层存储？是否需要去重（基于 `collection_id + filename + size` 或文件哈希）？
- `documents` 表是否预留 `md_text` 或 `md_text_path` 字段存储 MinerU 全文 Markdown？若仅存路径，请确认保存根目录与清理策略。
- `elements` 表中以下字段的类型/长度是否已在 Data_Model 定义清晰：`text_content`（长度上限）、`image_base64`（是否允许空）、`bbox_json`（JSON/text 类型选择）、`header_name/level_nav/header_level/order/page_no/elem_type`（枚举与约束）。
- 是否需要在 `documents` 记录中维护 `element_count` 与 `parsed_at`？

## 处理规则与边界
- 标题层级修复算法的细节：是否以 MinerU 头部检测为主，抑或允许通过正则/编号规则推断？标题跳级（如 1→1.2）是否需要强制补齐层级？
- 章节摘要生成方式：是否同意使用 `tfidf_summary` 的轻量方案？有无可直接使用的实现或依赖路径？摘要的长度上限与语言（中/英/混合）处理是否有要求？
- `image_base64` 是否需要去除 `data:image/...;base64,` 前缀？若 DB 体量受限，是否改为仅存文件路径并延后加载？
- `bbox` 原始坐标是像素坐标还是标准化坐标（0-1）？写入 `bbox_json` 是否保持 MinerU 原样？

## 性能与批量
- 批量入库策略是否采用 `batch_size=32`？是否需要事务包裹单文档的全部 elements（出错则整单回滚）？
- 单个 PDF 的最大体积与最大页数上限？是否需要在 API 层限制 `MAX_UPLOAD_MB`？

## 前端最小需求
- 前端是否仅需：上传 + 文档列表 两个最小视图？文档列表需要展示哪些字段（name/size/created_at/element_count/parse_status）？
- 是否暂不实现“查看 PDF 原文”和“高亮跳转”（按路线图应在 M5）？

## 兼容与版本
- 以当前 `docs/en/Data_Model.md` 为准还是即将更新的版本？若有字段命名差异，请给出最终版，避免重复迁移。
- M1 阶段 repositories 是否已经具备基本 CRUD 并合入主分支？`elements_repo.batch_insert` 是否允许我们按需扩展？

## 交付与验收
- 手工验证脚本位置与命名是否同意：`tests/manual/test_m2_ingest.py`？是否需要同时提供一个最简 curl 示例？
- 验收口径：是否以“能上传一个 PDF 并在文档列表看到记录，DB 中有相应 elements 行”为准？是否需要附带一份解析统计（各类型元素计数）截图/日志？

—— 请在以上问题处逐条确认或给出偏好，我们将据此最终敲定实现细节并开工。

