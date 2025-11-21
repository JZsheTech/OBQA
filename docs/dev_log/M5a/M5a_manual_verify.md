## M5a 人工验收步骤

1) 环境准备  
   - 确保后端已运行，`VITE_API_BASE`（默认 `http://127.0.0.1:9075/api`）指向实际服务；前端执行 `npm install`（若未安装依赖）后 `npm run dev`。  
2) AppShell 与主题  
   - 打开首页 `/`，确认顶栏 Logo/右侧头像、顶部标签（知识库主页/Chat 历史）与面包屑呈现；检查浅色主题、按钮/卡片/搜索条/徽标的统一风格。  
3) 健康检查封装  
   - 首页右侧“健康检查”卡自动触发 `/healthz`；状态为 OK 时显示绿色点与“后端健康”；将后端停掉或改错 `VITE_API_BASE` 后重试，应出现错误 toast。  
4) 请求封装与上传链路  
   - 在“快速文档台”输入真实 `collectionId`，点击“加载文档”查看表格刷新；点击“上传 PDF”选择文件，成功后 toast 提示并刷新列表（失败时 toast 报错）。  
5) Modal/Drawer 组件  
   - 点击“新建 Collection”打开 Modal，验证表单样式与按钮交互；点击“查看页面骨架”或“查看路由”打开 Drawer，确认路由占位列表展示。  
6) 路由骨架  
   - 访问 `/collections/{id}`、`/collections/{id}/documents/{docId}`、`/collections/{id}/chat/{chatId}`、`/documents/{docId}/chat/{chatId}`、`/chat-history`，检查 AppShell 持续存在、页面卡片与提示文案符合占位描述。
