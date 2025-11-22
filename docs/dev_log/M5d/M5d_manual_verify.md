## M5d 人工验收步骤

1) 环境启动  
   - 后端：`conda activate quest`，在 `EviQAsys/backend` 下运行 `uvicorn EviQAsys.backend.app.main:app --app-dir EviQAsys/backend --reload`，确保 OceanBase 可连通。  
   - 前端：`cd EviQAsys/frontend && npm install`（首次）后 `npm run dev`，浏览器打开对应端口。  
   - 数据准备：使用真实 Collection/Document 记录（通过 M5c 上传的真实 PDF 并已解析、嵌入）；严禁使用空白或模拟文件。

2) Document 页头与元信息  
   - 从 Collection 页点击任意文档或直接访问 `/collections/{collection_id}/documents/{document_id}`。  
   - 检查 breadcrumbs 显示 `Home / Collection / Document`，页头 title 为 document title/file_name，subtitle 显示 abstract 截断。  
   - 确认元信息卡片展示 collection 名、file_name、file_size、created_at、parse_status、num_pages、element_count、meta_info（截断）。  
   - 点击“返回 Collection”应跳转到对应 `/collections/{collection_id}`。

3) 打开原始 PDF  
   - 点击页头“打开原始 PDF”按钮，新标签页应直接下载/预览真实 PDF。  
   - 若文件缺失，前端应弹出错误 toast；接口返回 404。

4) Abstract 展示  
   - 在 Abstract 卡片中检查 MinerU 解析出的摘要是否可滚动查看；无摘要时显示空态提示而非报错。

5) Document 聊天历史  
   - 确认 `/api/documents/{document_id}/chats` 被调用，列表展示 chat title/type/created_at。  
   - 点击任一条目跳转到 `/documents/{documentId}/chat/{chatId}`；无数据时显示空态，点击“刷新”重新请求。

6) Document-RAG 检索  
   - 在检索输入框填写真实问题/关键词，切换向量或全文模式，设置 TopK（默认 5），点击“检索”。  
   - 验证请求 query 参数包含 `collection_id` 与 `doc_id={document_id}`。  
   - 列表展示截断的 text_content/score/elem_type，点击“查看全文”打开 Drawer，使用“复制”按钮后可在剪贴板粘贴验证。  
   - 更换搜索模式再次检索，确认 loading/空态/错误 toast 行为符合预期。

> 全部验收步骤均为手工操作，不使用自动化脚本；检索与聊天历史依赖真实解析与向量化数据。
