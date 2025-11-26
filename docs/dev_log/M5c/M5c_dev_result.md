## M5c 开发结果

- 后端接口：新增 `GET /api/collections/{id}` 返回 collection 元信息；`GET /api/collections/{id}/documents` 支持 `search_field=title|abstract|md_text` + `keyword` 模糊搜索，`DocumentListItem` 携带 `title/abstract/num_pages` 等字段；新增 `GET /api/collections/{id}/chats`（type=collection）用于聊天历史。仓储层补充 `DocumentsRepository.search_in_collection`，统一 parse_status 计算。
- 前端 API 封装：`listDocuments` 支持查询参数，新增 `getCollectionDetail`/`listCollectionChats`/`runRetrieval`；AppShell 顶部标记更新为 M5c collections-detail。
- Collection 管理页：展示 collection name/description/created_at；文档列表区分“全部/搜索结果”视图，支持 title/abstract/md_text 搜索与 Reset，点击条目跳转 Document 页；加载/空态/错误 toast 完整。
- 上传与聊天历史：多文件选择后串行调用上传接口，队列展示上传/失败状态并可刷新列表；聊天历史从 `/api/collections/{id}/chats` 读取，列表可跳转到 Collection Chat。
- 简单 Collection-RAG：输入关键词 + 模式切换（hybrid/vector/fulltext）调用 `/api/retrieval/test`，展示 score/elem_type/doc_id 等元信息；支持复制与详情 Drawer 查看全文。

### 已知限制 / 后续衔接
- 文档列表未分页，适用于当前数据量；搜索使用 SQL LIKE，`md_text` 较大时查询可能偏慢。
- 上传队列为串行执行，未提供取消/重试；需等待 MinerU 同步解析完成后元素数量才会刷新。
- Chat 历史仅展示已有记录，创建/编辑聊天仍待 M5e 阶段完成。
- RAG 依赖已向量化的元素；未嵌入或向量化失败时结果可能为空。未覆盖元素 bbox/PDF 高亮展示，留待聊天页实现。
