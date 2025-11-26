## M5c 人工验收步骤

1) 环境启动  
   - 后端：`conda activate quest`，在 `EviQAsys/backend` 下运行 `uvicorn EviQAsys.backend.app.main:app --app-dir EviQAsys/backend --reload`，确认 OceanBase 可连通。  
   - 前端：`cd EviQAsys/frontend && npm install`（首次）后 `npm run dev`，浏览器打开对应端口。  
   - 数据准备：使用真实 Collection/Document 记录；如无数据，可先在首页创建 Collection 并上传实际 PDF。

2) Collection 元信息  
   - 访问 `/collections/{collection_id}`，检查页头显示 name/description/created_at，与数据库一致；刷新页面确保 `GET /api/collections/{id}` 正常返回。

3) 文档列表与搜索视图  
   - “全部文档”区域应列出 collection 下全部文档，显示 title/file_name/parse_status/element_count/num_pages。点击任一条跳转到对应 Document 页。  
   - 在搜索框选择 `title` 或 `abstract`，输入真实关键字并搜索，列表切换到“搜索结果”视图并显示结果数；切换为 `md_text` 关键词重复验证。  
   - 点击 Reset 后搜索结果清空，回到全量列表，空态时展示提示。

4) 多文件上传  
   - 使用页头或“上传 PDF”区域选择多个真实 PDF（非空白文件），点击“开始上传”；队列应显示 uploading/success/error 状态。  
   - 上传成功后触发列表刷新，出现新文档，parse_status 显示 uploaded/parsed，文件大小与名称正确；错误文件应提示失败原因。

5) Collection 聊天历史  
   - 卡片应调用 `/api/collections/{id}/chats` 展示已有聊天条目（title/创建时间/type），点击条目跳转到 `/collections/{id}/chat/{chat_id}`。  
   - 无聊天数据时展示空态文案。

6) 简单 Collection-RAG  
   - 在 RAG 区域输入真实问题/关键词，选择混合/向量/全文模式，设置 TopK（默认 5）后点击“检索”。  
   - 检索结果列出 element_id/doc_id/elem_type/score，文本为截断的 `text_content`。点击“查看全文”弹出 Drawer 展示全文，点击“复制”后可在剪贴板中粘贴验证。  
   - 将搜索模式切换为其他模式重复验证，确认 `/api/retrieval/test` 请求携带 `collection_id` 和 `search_mode` 参数。

> 全部验收步骤均为手工操作，不使用模拟数据或自动化脚本；检索与上传需依赖 MinerU 解析与真实向量数据。
