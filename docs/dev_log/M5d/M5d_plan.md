## M5d Document 管理页实施方案

### 目标与范围
- 按《开发路线图》M5d DoD 落地 Document 管理页：展示 document 元信息（collection/title/file_name/num_pages/element_count）、Abstract、Document 聊天历史、Document-RAG 检索，以及“打开原始 PDF”入口。
- 后端补齐缺失接口：document 详情、document 聊天历史、PDF 下载；复用检索接口支持 doc_id 过滤，确保前端能按文档维度检索。
- 前端在现有设计系统上完成 Document 页布局与交互，保持与 dependency/frontUI_design 的视觉方向一致但用 React 实现。

### 关键设计与接口决策
- **Document 详情数据面**：新增 `GET /api/documents/{document_id}` 返回 `DocumentRead` 扩展体，字段含 `collection_id/collection_name/title/file_name/num_pages/element_count/abstract/meta_info/md_text/created_at/parse_status`，`parse_status` 由 `element_count` 计算，404 时返回 envelope 错误。
- **Document 聊天历史**：新增 `GET /api/documents/{document_id}/chats`，仅返回 `type=document` 的 chat，按创建时间倒序；前端条目点击跳转 `/documents/{document_id}/chat/{chat_id}`。
- **PDF 下载**：新增 `GET /api/documents/{document_id}/file` 直接流式返回文件，文件名回落到 `file_name`，校验 doc 是否存在且路径位于 `UPLOAD_DIR`；不存在返回 404。
- **Document-RAG**：沿用 `/api/retrieval/test`，必传 `collection_id`，附加 `doc_id` 过滤；前端提供关键词输入、检索模式（hybrid/vector/fulltext）、TopK，列表截断展示并提供 Drawer 查看全文与复制。
- **导航/面包屑**：PageHeader breadcrumbs 采用 `Home / Collection 名 / Document 名`；顶部 AppShell 标记更新为 “M5d document-detail”。

### 后端任务拆解
1) 仓储：`ChatsRepository` 增加 `list_by_document(document_id)`；`DocumentsRepository` 增加读取 collection 名/parse_status 的封装（或在路由中组合）。
2) 路由：新增 `api/routes/documents.py`，注册 3 个接口（详情 / chats / file），校验 doc 存在与 collection 关联，封装 envelope。
3) 复用检索：保持 `/api/retrieval/test` 支持 `doc_id` 过滤，错误提示保持一致；必要时补充参数校验。

### 前端任务拆解
1) API 客户端：新增 `getDocumentDetail`、`listDocumentChats`、`buildDocumentFileUrl`（返回下载 URL）；`runRetrieval` 支持 docId 透传。
2) 页面数据流：`DocumentDetail` 加载 document 详情 + collection 详情，展示 meta chips（collection/title/file_name/num_pages/element_count/created_at/parse_status），提供“返回 Collection”与“打开原始 PDF”按钮。
3) Abstract 卡片：滚动展示 abstract，空态提示；附加 md_text 预览入口留待后续。
4) Document-RAG：关键词 + 模式 + TopK，调用 `/api/retrieval/test`（带 doc_id），列表/Drawer/复制交互与加载/错误/空态提示完整。
5) 聊天历史：读取 `/api/documents/{document_id}/chats`，展示 chat title/type/created_at，点击跳转 Document Chat；空态/刷新按钮。

### 风险与假设
- OceanBase LIKE 查询在 md_text 上可能较慢，Document-RAG 仍依赖已完成向量化；未嵌入时检索可能为空。
- 上传文件若被人工删除导致文件路径不存在，PDF 下载接口需优雅返回 404 提示。
- 当前聊天创建仍未开放，文档聊天历史可能为空；M5e 继续完善。

### 完成判定（DoD 对应）
- `/api/documents/{document_id}` 返回 document 元信息与 parse_status，404/错误路径返回 envelope。
- Document 页展示 collection/title/file_name/num_pages/element_count/created_at/parse_status，Abstract 可滚动查看。
- `/api/documents/{document_id}/chats` 可返回文档级聊天列表，页面可跳转到 Document Chat。
- Document-RAG 输入可带 doc_id 成功检索并显示截断文本/详情 Drawer/复制。
- “打开原始 PDF” 按钮可拉起实际文件或在缺失时提示失败。
