## M5c Collection 管理页实施方案

### 目标与范围
- 按《开发路线图》M5c DoD 落地 Collection 管理页：展示 collection 元信息、文档列表（全部/搜索视图）、多文件上传、collection 聊天历史、简单 Collection-RAG 检索。
- 后端补齐缺失接口：collection 详情、collection 下文档搜索、collection 聊天列表，确保前端调用 `/api/collections/{id}/documents`、`/api/retrieval/test` 能覆盖搜索/检索需求。
- 前端继续复用 M5a/M5b 的设计系统与 envelope 请求封装，保持与 dependency/frontUI_design 的布局与交互逻辑一致但以 React 实现。

### 关键设计与接口决策
- **Collection 基础信息**：新增 `GET /api/collections/{id}` 返回 `CollectionRead`（id/name/description/created_at），前端页头展示并作为子页面跳转基准。
- **文档列表 + 搜索**：`GET /api/collections/{id}/documents` 支持 `search_field=title|abstract|md_text` + `keyword`（大小写不敏感 LIKE），默认返回全部。响应结构扩充 `DocumentListItem` 以携带 `title/abstract/num_pages` 等元信息，parse_status 继续由后端计算。前端区分“全部”与“搜索结果”视图，显示搜索标签与 Reset。
- **上传入口**：沿用 `/api/collections/{id}/documents` 单文件入口，前端允许多选后串行上传（展示进行中的文件名/进度/错误 toast），上传完成后刷新列表。保留后端 PDF 扩展名校验与重复检测。
- **Collection 聊天历史**：新增 `GET /api/collections/{id}/chats`（type=collection），按创建时间倒序返回 `ChatRead`；前端列表条目可点击跳转 `/collections/{id}/chat/{chat_id}`，空态提示。
- **简单 Collection-RAG**：复用 `/api/retrieval/test`，必传 `collection_id`，可选 `search_mode=hybrid|vector|fulltext`、`top_k`、`doc_id`。前端提供关键词输入 + 模式切换，列表展示截断 `text_content`，详情弹窗支持复制。
- **顶栏标记**：AppShell 顶部里程碑标记更新为 M5c collections-detail，便于识别当前阶段。

### 后端任务拆解
1) 新增 collection 详情路由；对不存在 id 返回 404 envelope 错误。  
2) 扩展 documents_repo：增加按 `title/abstract/md_text` 模糊搜索方法；调整列表 API 支持查询参数并返回丰富字段。  
3) 补充 collection 聊天列表 API：调用仓储 `list_by_collection`，返回 `ChatRead` 列表。  
4) 保持上传/检索现有接口兼容性，必要时补充参数校验与错误信息。

### 前端任务拆解
1) API 封装：`listDocuments` 支持查询参数；新增 `getCollectionDetail`、`listCollectionChats`、`runRetrieval` 封装。  
2) 页面布局：CollectionDetail 左列文档列表 + 搜索 + 上传进度，右列聊天历史 + Collection-RAG；页头展示元信息/创建时间。  
3) 文档交互：搜索下拉（title/abstract/md_text）、Searched result 标签、Reset；点击条目跳转 Document 页。  
4) 上传交互：多文件选择、上传队列状态（成功/失败 toast）、刷新列表。  
5) 聊天历史：列表展示 chat title/fallback 名称 + 创建时间，跳转 collection chat。  
6) RAG 结果：关键词输入 + 模式切换，检索结果列表 + 详情 Drawer（全文/复制），空态/加载/错误提示。

### 风险与假设
- MinerU 同步解析耗时，前端上传队列需显示状态以免误解为卡死；未做取消/重试。  
- OceanBase 上对 `md_text` LIKE 可能较慢，先限制返回条数与字段，不做全文摘要。  
- 若集合暂无 chat 数据，聊天历史为空态；Chat 创建留待 M5e。  
- 检索效果依赖已有向量化结果，未向量化时可能返回空列表。  
- 文档列表暂不分页，假设单 Collection 文档数可一次性加载。

### 完成判定（DoD 对应）
- Collection 页展示 name/description/created_at。  
- `/api/collections/{id}/documents` 支持 title/abstract/md_text 搜索，前端区分全部/搜索结果，空态可见。  
- 上传入口支持多文件串行上传，成功/失败有 toast，列表可刷新。  
- `/api/collections/{id}/chats` 可返回聊天历史，前端列表可点击跳转。  
- Collection-RAG 输入可触发 `/api/retrieval/test` 检索并展示/复制 text_content，支持搜索模式切换（含混合模式）。
