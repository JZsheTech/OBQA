## M5b 人工验收步骤

1) 环境启动  
   - 后端：`conda activate quest`，在 `EviQAsys/backend` 下运行 `uvicorn EviQAsys.backend.app.main:app --app-dir EviQAsys/backend --reload`，确认 OceanBase 可连通。  
   - 前端：`cd EviQAsys/frontend && npm install`（首次）后 `npm run dev`。浏览器访问首页 `/`。
2) 列表加载  
   - 打开首页即触发 `GET /api/collections`，检查页面出现集合卡片栅格；若无数据，显示空态与“去创建”按钮。  
   - 查看右侧“系统状态”卡，确认 API 基址展示正常，健康检查点亮绿色（停掉后端应出现错误 toast）。
3) 搜索与 Reset  
   - 在搜索框选择 `按 name 搜索`，输入已存在集合名关键词，点击“搜索”后列表应更新且出现 “Searched result” 标签，显示实际结果条数。  
   - 切换为 `按 description 搜索`，输入描述片段重复上述操作。点击 Reset 或清空输入后刷新出全量列表，标签消失。
4) 新建 Collection  
   - 点击右上角 “+ 新建 Collection”，在弹窗中填写名称（必填）与描述（可空），点击“创建”。成功后出现成功 toast，弹窗关闭，列表刷新并可看到新集合（若当前有过滤条件则继续沿用）。  
   - 输入空名称应被前端禁用，若后端返回错误则弹出错误 toast。
5) 跳转检查  
   - 点击任意集合卡片，浏览器应跳转到 `/collections/{id}`，顶部标签栏保持“知识库主页”选中状态。使用浏览器返回键可回到列表，搜索条件保持输入值。

以上步骤均依赖真实后端接口和数据库记录，不使用模拟数据。验收时可结合浏览器 Network 面板确认 `search_field/keyword` 查询参数随搜索请求发送。
