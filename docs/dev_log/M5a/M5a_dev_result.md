## M5a 开发结果

- 设计系统：重写 `src/index.css` / `App.css`，定义品牌色、灰阶、强调色、空间/圆角/阴影 token，导入 Space Grotesk + IBM Plex Sans 字体，统一按钮、卡片、搜索条、徽标、空态、Modal/Drawer、Toast 的样式基准。
- 工程骨架：新增 AppShell（顶栏、顶级标签、面包屑容器），路由覆盖 `/`、`collections/:id`、`collections/:id/documents/:docId`、`collections/:id/chat/:chatId`、`documents/:docId/chat/:chatId`、`/chat-history`，统一 PageHeader/Breadcrumb 入口。
- 基础组件：创建 Button、SearchBar、Modal、Drawer、ToastProvider、StatusPill、PageHeader 等可复用单元，并在首页实际使用，保证 DoD 所需的 AppBar/TopTabs/Breadcrumb/SearchBar/Button/Modal/Drawer 均可见。
- API 封装：重写 `src/api/client.js`，封装 `request()` 解析 `{"code":"OK"}` envelope，透传 FormData，推导健康检查基址，错误抛出结构化 `ApiError`；健康检查单独旁路 `/healthz`。
- 功能迁移：将健康检查 + 文档上传/列表迁入新 `CollectionsHome` 页面，保留 collectionId 输入、上传表单、刷新文档表格，并用 Toast 提示错误/完成。
- 路由占位：为 Collection/Document 管理、Collection chat、Document chat、Chat 历史提供骨架卡片与文案，标注 M5b–M5f 的待接入内容，便于后续迭代联调。

### 已知限制 / 后续衔接
- Collections Home 中的“新建 Collection”仅展示表单与 Modal，未调用后端接口；需在 M5b 接入 `POST /api/collections`。
- Collection/Document 详情、RAG、聊天页面当前为布局占位，未绑定真实数据/接口；M5b–M5f 需逐步对接。
- 未执行自动化测试；未新增依赖，保持现有 `npm run dev` 启动流程。
