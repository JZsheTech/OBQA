## M5e 人工验收步骤

1) 环境启动  
   - 后端：`conda activate quest`，在 `EviQAsys/backend` 下运行 `uvicorn EviQAsys.backend.app.main:app --app-dir EviQAsys/backend --reload`，确保 OceanBase 与向量化数据可用。  
   - 前端：`cd EviQAsys/frontend && npm install`（若未安装依赖）后 `npm run dev`。  
   - 数据：使用已解析并完成嵌入的真实 Collection/Document（如 sample_data/converted_doc 下的 PDF），严禁使用空文档或 mock 数据。

2) 进入 Collection Chat 页面  
   - 从 Collection 管理页点击任意聊天条目或直接访问 `/collections/{collectionId}/chat/{chatId}`。  
   - 验证 `/api/chats/{chatId}` 请求成功，返回 turns、`evidence_no_mapping`，页面聊天流显示用户/助手气泡与 `[Evidence#no]` 标签。

3) 新建聊天  
   - 点击“新建聊天”按钮，输入可选标题后确认。  
   - 观察 `/api/collections/{collectionId}/chats`（POST）成功返回新 chat_id，Sidebar 列表刷新并高亮新会话，路由跳转到新聊天页。  
   - 若创建失败应弹出错误 toast。

4) 发送问题与 Evidence 标签  
   - 在输入框填写真实问题，点击“发送”。请求 `/api/chats/{chatId}/turns` 应返回 `answer_text` 含 `[Elem#id]` 且 `evidences` 内带 `evidence_no`。  
   - 聊天流刷新后应展示 `[Evidence#no]` 标签；点击任意标签可触发 `GET /api/turns/{turnId}/evidences`（若需）并在右侧显示选中证据元信息。

5) PDF 高亮与文档切换  
   - 确认中间 PDF Viewer 通过 `react-pdf-viewer` 渲染选中文档；点击 Evidence 标签后：  
     - 文档下拉自动切换到 evidence 的 `document_id`；  
     - Viewer 跳转到对应页码（page_index-1）并显示半透明 bbox 高亮；  
     - 若 bbox 缺失，仅在右侧提示“缺少 bbox，高亮不可用”。  
   - 手动切换文档下拉后，高亮应消失（跨文档不渲染），点击“打开原始 PDF”应在新标签页展示真实文件。

6) Sidebar 聊天列表切换  
   - 在右侧列表选择其他聊天，路由应更新，聊天流与 PDF 联动信息随之刷新。  
   - 列表刷新按钮可重新加载 `/api/collections/{collectionId}/chats`，空列表时展示空态而非错误。

> 全部操作需人工观察界面与网络请求，无自动化脚本；证据信息、bbox 与跳转均依赖真实解析和向量检索数据。
