## M5f Document Chat 页面实施方案（两栏 + Sidebar）

### 目标与范围
- 按《开发路线图》M5f DoD 落地单文档聊天：固定 doc_id 的聊天流可发送问题并渲染证据，高亮对应 PDF；侧边栏列出 document 级聊天历史并可切换。
- 衔接现有 Collection Chat 能力：复用 `[Evidence#no]` 解析与 PDF 高亮逻辑，校验 chat.document_id 与路由 doc_id 一致。
- Document 管理页补齐文档聊天创建入口，保持“打开原始 PDF”入口与聊天/侧边栏状态一致。

### 关键设计与接口决策
- **文档级聊天创建**：扩展 `POST /api/collections/{collection_id}/chats` 支持 `doc_id`，校验文档归属后以 `type=document` 创建聊天；前端新增 `createDocumentChat` 封装。
- **聊天加载与校验**：仍用 `GET /api/chats/{chat_id}` 取聊天与 turns，若类型/文档不匹配当前路由给出警告并禁用发送；侧边栏使用 `GET /api/documents/{doc_id}/chats`。
- **PDF 高亮**：复用 Collection Chat 的 bbox 解析（unit/0-1000 坐标缩放到 PDF 实际尺寸）与 `react-pdf-viewer` 高亮层，固定单文档，无下拉切换；缺失 bbox/page_index 提示降级。
- **交互布局**：左侧聊天流 + QA 控制（检索模式、搜索模式、TopK、元素类型、历史轮数、VQA/记忆开关）；右侧固定 PDF Viewer + 选中证据元信息卡；抽屉式 Sidebar 列出文档聊天并可创建/切换。
- **Document 页衔接**：在 Document 详情页新增“新建 Document Chat”按钮，通过 doc_id+collection_id 创建后跳转；空态提示更新。

### 任务拆解
1) **后端**：
   - 扩展 ChatCreateRequest 接收 doc_id，`create_collection_chat` 校验文档归属后创建 `type=document` 聊天。
2) **前端 API**：
   - `createCollectionChat` 支持 docId，新增 `createDocumentChat`；DocumentDetail 使用新接口创建文档聊天。
3) **Document Chat UI**：
   - 重写 `DocumentChat.jsx`：聊天生命周期（加载/发送/重命名）、证据标签解析、PDF 高亮、缺失 bbox/page 提示、Drawer 聊天列表。
   - 固定单文档 PDF 工具栏 + 原始 PDF 打开入口；证据弹窗支持复制 snippet/text_content。
4) **文档与验收**：在 `docs/dev_log/M5f` 记录计划、开发结果与人工验收步骤。

### 风险与假设
- 数据需包含真实 bbox/page_index；缺失时仅提示不跳转。多 bbox 仅按单页渲染提示。
- 依赖已有 QA Flow/向量检索通路（M3-M4 已打通），未对检索质量做额外校准。
- `pdfjs` 构建仍有 chunk 体积/`eval` 警告，为已知三方特性暂不收敛。

### 完成判定（对照 DoD）
- 可以创建 document 类型聊天并在 Sidebar 列出/切换；加载聊天时校验 doc_id/type，异常提示。
- 聊天流可发送问题，回答展示 `[Evidence#no]` 标签，点击跳转到固定 PDF 并高亮 bbox；无 bbox/page 时提示降级。
- PDF Viewer 固定单文档，支持缩放/跳页与“打开原始 PDF”；选中证据信息在右侧卡片可见。
- Document 详情页提供文档级聊天创建入口并可跳转到新聊天。
