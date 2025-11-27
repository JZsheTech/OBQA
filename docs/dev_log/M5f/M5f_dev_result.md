## M5f 开发结果与人工验收

### 交付摘要
- **后端**：`POST /api/collections/{collection_id}/chats` 支持 `doc_id`，校验文档归属后创建 `type=document` 聊天；保留原 collection 聊天逻辑。
- **API 客户端**：`createCollectionChat` 支持 docId，新增 `createDocumentChat` 便于文档页/文档聊天页创建；DocumentDetail 增加“新建 Document Chat”入口与空态提示。
- **Document Chat 页面**：重写为双栏布局 + 抽屉 Sidebar，固定单文档 PDF 高亮；支持聊天加载/重命名/发送、QA 控制（检索模式/搜索模式/TopK/元素类型/历史轮数/VQA/记忆）、证据标签跳转与高亮、bbox/page 缺失提示、证据弹窗复制。
- **安全校验**：加载聊天时校验 `chat.type=document` 且 `document_id` 与路由一致，异常时禁用发送并提示；证据所属文档不一致时高亮禁用并提示。
- **构建验证**：前端执行 `npm run build` 通过（pdf.js 体积/`eval` 警告属三方提示）。

### 手工验收步骤（仅人工观察，无自动化测试）
1) **启动服务**  
   - 后端：`conda activate quest`，在 `EviQAsys/backend` 运行 `uvicorn EviQAsys.backend.app.main:app --app-dir EviQAsys/backend --reload`。  
   - 前端：`cd EviQAsys/frontend && npm install`（首次）后 `npm run dev`。  
   - 数据：使用真实已解析并向量化的文档（严禁 mock）。
2) **创建文档级聊天**  
   - 打开 Document 详情页 `/collections/{collectionId}/documents/{documentId}`，点击“新建 Document Chat”；请求 `POST /api/collections/{collectionId}/chats` 应带 `doc_id` 成功返回 chat_id 并跳转。  
   - 文档聊天空态提示应更新，Document 聊天列表 `/api/documents/{documentId}/chats` 可看到新会话。
3) **加载聊天与证据渲染**  
   - 访问 `/documents/{documentId}/chat/{chatId}`，观察聊天流加载，右上警告不存在（`type=document` 且 doc_id 匹配）。  
   - 回答中的 `[Evidence#no]` 标签可点击，若证据 doc_id 与当前文档匹配则 PDF 跳转到 `page_index-1` 并显示 bbox；无 bbox/page_index 显示降级提示。
4) **PDF 与侧边栏**  
   - PDF Viewer 显示固定文档，缩放/重置可用；“打开原始 PDF”在新标签页展示真实文件。  
   - Drawer “聊天列表” 拉取 `/api/documents/{documentId}/chats`，当前聊天高亮，可切换到其他文档聊天；列表为空时展示空态。
5) **聊天交互与 QA 控制**  
   - 在输入框填写真实问题，调整检索/搜索模式、TopK、元素类型或历史轮数等，再点击“发送”；请求 `POST /api/chats/{chatId}/turns` 成功后聊天流刷新。  
   - 若切换到错误 doc_id 的聊天或非 document 类型，页面出现警告并禁止发送。
6) **证据弹窗与复制**  
   - 点击 PDF 高亮矩形弹出证据详情，尝试“复制文本内容”应复制 snippet/text_content；无内容时提示。

> 所有验证需人工查看界面与网络请求，无自动化脚本；确保使用真实解析数据和数据库记录。
