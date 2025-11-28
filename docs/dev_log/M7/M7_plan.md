## M7 arXiv 集成开发计划

### 目标与范围
- 将 `dependency/arxiv_search_demo` 的检索/收藏能力接入主系统，提供 arXiv 搜索页与收藏夹页。
- 新增 `arxiv_favorite_doc` 表并与 `documents` 互相关联，支持将收藏的论文一键导入既有 Collection（含解析与向量化）。
- 提供可复用的后端接口（搜索、收藏、更新、删除、导入），并在前端提供完整流程与反馈。

### 关键设计
- **数据模型**：`arxiv_favorite_doc` 持久化 arXiv 元信息（id/version/title/summary/authors/categories/urls/tags/note/published/updated），可选 `document_id` 外键；`documents` 新增可空 `arxiv_favorite_id` 外键，双向约束（删除任意一侧将对方置空）。
- **搜索接口**：POST `/api/arxiv/search` 接收字段/时间/排序参数，调用内部 arXiv 客户端（限制 `max_results<=50`）返回标准化列表。
- **收藏接口**：POST `/api/arxiv/favorites` 保存/更新元信息与 tags/note；GET `/api/arxiv/favorites` 支持分页/关键词/作者/分类/标签筛选；PATCH/DELETE 针对单条。
- **导入接口**：POST `/api/arxiv/favorites/{favorite_id}/import` 传入 `collection_id`，下载 PDF→调用 `DocumentIngestor.ingest_path`→调度 `DocumentIndexer.embed_document`，并写回双向外键。
- **前端路由**：新增“arXiv 搜索”和“arXiv 收藏夹”页面；搜索页支持条件检索+收藏操作；收藏夹页展示筛选/分页、编辑 tags/note、删除、导入到 Collection（可选集合下拉），并提示导入状态。

### 任务拆解
1) **Schema/仓储层**：扩展 `schema.sql`、`DocumentsRepository`，新增 `ArxivFavoritesRepository`（CRUD/筛选/联动更新）。
2) **服务/接口**：封装 `services/integrations/arxiv_client.py` 搜索工具；新增 FastAPI 路由 `api/routes/arxiv.py`（搜索/收藏/导入）并整理 Pydantic 模型。
3) **前端 API & 页面**：扩展 `src/api/client.js` 调用；新增 `pages/ArxivSearch.jsx` 与 `pages/ArxivFavorites.jsx`、必要的 UI 组件与导航入口，复用现有布局/Toast。
4) **文档与验收**：在 `docs/dev_log/M7` 记录开发结果与手工验证步骤。

### 风险与依赖
- arXiv PDF 下载可能失败或返回非 PDF：需健壮错误提示并清理临时文件。
- MinerU/向量服务需可用，否则导入后嵌入后台任务会失败（需日志提醒）。
- OceanBase 现存数据需保持兼容，DDL 采用幂等 ALTER/外键 NULL 处理。
