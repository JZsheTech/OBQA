## M5a 设计系统 / 工程底座实施方案

### 目标与范围
- 对照《开发路线图》M5a DoD，落地全局样式 token、基础组件（AppBar/TopTabs/Breadcrumb/SearchBar/Button/Modal·Drawer），并建立 AppShell 与完整路由骨架（Collections Home、Collection Detail、Document Detail、Collection Chat、Document Chat、Chat History）。
- 重写前端 `fetch` 封装以适配 `{"code":"OK","data":...}` envelope，支持 `VITE_API_BASE` 与健康检查旁路，统一错误提示与日志钩子。
- 将现有健康检查与文档上传/查询功能迁入新框架，保证 Demo 可继续使用。

### 关键设计决策
- **设计 Token：** 提取 `dependency/frontUI_design` 的色板/间距为参考，重新命名与微调数值（品牌蓝主色、灰阶文本、强调/危险/成功色，8px 间距网格，圆角/阴影、字体栈以几何无衬线为主），写入 `:root` CSS 变量并在 `App.css/index.css` 复用。
- **基础组件：**
  - AppShell：顶栏（Logo + 用户头像占位）+ 二级顶部标签（“知识库主页”“Chat 历史”）+ 面包屑区域 + 内容容器。
  - UI 元件：`<Button variant=primary/ghost/tonal>`、`<SearchBar filter>`、`<Badge/Chip>`、`<Card>`、列表项骨架、空态占位。
  - 弹层：`Modal` 覆盖层 + `Drawer`（右侧滑出）用于未来聊天历史/过滤器。
- **路由骨架：** React Router 嵌套在 AppShell 下，预留路径：
  - `/` Collections Home
  - `/collections/:collectionId` Collection Detail
  - `/collections/:collectionId/documents/:documentId` Document Detail
  - `/collections/:collectionId/chat/:chatId` Collection Chat
  - `/documents/:documentId/chat/:chatId` Document Chat
  - `/chat-history` Chat 历史
  - 未匹配页给出空态提示。
- **API 封装：** `request(path, options)` 统一处理 envelope，默认 `Content-Type: application/json`（FormData 透传），错误抛出结构化对象；健康检查自动从 `VITE_API_BASE` 推导 host；集中日志/错误钩子便于接入 toast。

### 开发任务拆解
1) 样式底座：重写 `index.css/App.css`，声明 token、排版规范、滚动条/表单基础样式，去除 Vite 默认暗色方案。  
2) 布局与组件：新增 AppShell、TopBar、TopTabs、Breadcrumb、PageHeader/Card/Button/SearchBar/Modal/Drawer/Toast 组件，提供可复用的列表行/空态样式。  
3) 路由与页面骨架：按上方路径创建页面文件并接入 AppShell；Collections Home 内放置“健康检查 + 快速上传/文档列表”区块替换旧页面。  
4) API 层：实现 envelope 版 `client`、`healthCheck`、`listDocuments`、`uploadDocument`，集成全局 toast 错误提示。  
5) 文档与验收：更新本计划、开发记录、人工验收说明。

### 依赖与假设
- 依赖 `react-router-dom` 已存在；不引入额外 UI 库，全部自定义样式。
- 后端仍暴露 `GET /healthz`、`GET/POST /api/collections/{id}/documents`；其他路由暂以占位符页面代替，待 M5b–M5g逐步对接。

### 完成判定（与 DoD 对应）
- 看到统一的浅色主题与 token（色板/字体/间距）；AppShell 顶栏、标签、面包屑可在所有页面骨架中展示。
- 基础组件可复用：按钮、搜索条、卡片、列表态、Modal/Drawer 具备样式与开关逻辑。
- API 封装能解析 `code:"OK"`，错误以 toast 呈现；`VITE_API_BASE` 生效，健康检查可运行。
- Collections Home 页面包含并可操作健康检查、collection 输入 + 文档列表、上传表单；旧版页面不再裸露。
