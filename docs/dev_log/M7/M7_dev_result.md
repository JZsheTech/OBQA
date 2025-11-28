## M7 开发结果与人工验收

### 交付摘要
- **数据模型扩展**：新增 `arxiv_favorite_doc` 表（arXiv 元信息、tags/note、可空 `document_id` 外键），`documents` 表新增可空 `arxiv_favorite_id` 外键，双向约束均为 `ON DELETE SET NULL`，幂等 DDL 已写入 `repositories/sql/schema.sql`。
- **后端接口**：新增 `/api/arxiv/search`（arXiv 检索）、`/api/arxiv/favorites` CRUD 与筛选、`/api/arxiv/favorites/{id}/import` 将收藏论文下载 PDF→解析→入库并触发向量化。引入 `ArxivFavoritesRepository`、`ArxivImportService`、内置 arXiv 搜索客户端（无外部依赖）。
- **文档 ingest 打通**：`DocumentIngestor` 支持可选 `arxiv_favorite_id`，导入成功后自动回填两表外键并异步调度 `DocumentIndexer.embed_document`。
- **前端体验**：新增 “arXiv 搜索”“arXiv 收藏夹” 页面与导航入口；支持多字段检索、收藏、筛选/排序收藏、编辑 tags/note、删除、选择 Collection 一键导入；API 客户端补充 arXiv 相关方法。

### 手工验收步骤（人工观测，无自动化测试）
1) **启动服务**
   - 后端：`conda activate quest`，在 `EviQAsys/backend` 运行 `uvicorn EviQAsys.backend.app.main:app --app-dir EviQAsys/backend --reload`，首启会自动迁移新表/外键。
   - 前端：`cd EviQAsys/frontend && npm install`（首次）后 `npm run dev`。
2) **arXiv 搜索与收藏**
   - 访问 `/arxiv/search`，输入关键词/作者/分类，点击“搜索”应看到 arXiv 返回的论文列表（标题/作者/摘要/分类）。
   - 点击某条的“加入收藏夹”，应提示成功；可重复搜索并收藏多条。
3) **收藏夹筛选与备注**
   - 打开 `/arxiv/favorites`，应显示收藏列表与总数；尝试按关键词/作者/分类/标签筛选并应用，列表更新且分页信息正确。
   - 在某条收藏下编辑 Tags/Note 并点击“保存备注”，弹出成功提示后列表数据刷新。
4) **导入到问答系统**
   - 在收藏夹页选择一个已有 Collection（需预先存在），对未导入的论文点击“导入到 Collection”；成功后该条显示“已关联 Document #X”。
   - 前往对应的 Collection 文档列表，确认新增 Document（文件名为 arXiv id/title 前缀），解析状态从 uploaded→parsed，向量化任务后台进行。
5) **删除与链路校验**
   - 在收藏夹页删除一条收藏，确认列表与总数减少；若该收藏已导入 Document，其 `documents.arxiv_favorite_id` 应自动置空（可通过后端日志/数据库检查）。

> 本次未执行自动化测试；所有验证需基于真实 arXiv 返回数据与实际 PDF 解析/向量化链路。
