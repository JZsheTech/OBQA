## M5d 开发结果

- 后端接口：新增 `GET /api/documents/{document_id}`（返回 Document 详情，含 collection_name/parse_status/abstract/meta_info 等）、`GET /api/documents/{document_id}/chats`（仅 document 类型聊天历史）、`GET /api/documents/{document_id}/file`（校验上传目录后流式返回 PDF）。仓储层增加 `ChatsRepository.list_by_document`，新增 `DocumentDetail` schema 支撑上述响应。
- 前端 API 客户端：新增 `getDocumentDetail`、`listDocumentChats`、`buildDocumentFileUrl`，`runRetrieval` 继续透传 docId；AppShell 顶栏阶段标记更新为 “M5d document-detail”。
- Document 管理页：`DocumentDetail` 页面接入真实数据，展示 collection/title/file_name/num_pages/element_count/parse_status/file_size/created_at/meta_info；Abstract 卡片可滚动查看；“打开原始 PDF” 直接新标签页访问下载接口；Breadcrumbs 按 `Home / Collection / Document` 组织。
- Document-RAG 与聊天历史：页面内提供 doc_id 过滤的检索输入（向量/全文模式 + TopK），列表截断显示并支持 Drawer 查看全文、复制；聊天历史从 `/api/documents/{id}/chats` 加载，点击跳转 `/documents/{documentId}/chat/{chatId}`，空态/加载/刷新提示齐全。

### 已知限制 / 后续衔接
- PDF 若被手动删除或移出 `UPLOAD_DIR`，下载接口会返回 404，前端仅提示失败未做重试。
- meta_info 在前端以截断文本展示，未做结构化展开；md_text 仅在详情响应中返回，未在页面展开以避免巨长文本。
- 聊天创建仍未在 Document 页开放，历史列表可能为空；Document RAG 依赖已完成的嵌入，未嵌入时结果为空。
- 未运行自动化测试，需按照手工验收步骤验证。
