## M5b 开发结果

- 后端接口：`GET /api/collections` 支持 `search_field=name|description` + `keyword` 模糊搜索（大小写不敏感，空 keyword 回落全量）；新增 `POST /api/collections` 使用 `CollectionCreate` 校验名称必填，返回 `{"code":"OK","data":CollectionRead}`。仓储层补充 `search_collections`（按创建时间倒序）。
- 前端 API 封装：`src/api/client.js` 新增 `listCollections`（带查询参数）与 `createCollection`，沿用 envelope 解析；保留健康检查/文档接口。AppShell 顶部标记更新为 M5b collections。
- Collections Home：页面改为真实数据驱动，首屏调用 `/api/collections`；搜索框支持 name/description 下拉，输入关键字后显示 “Searched result” 标签与结果条数，Reset 清空过滤并重新请求；加载态/空态均有反馈。
- 新建流程：弹窗校验必填名称，提交调用 `POST /api/collections` 后 toast 成功，自动刷新列表（保留当前过滤条件）；描述可空，输入会传递给后端。
- UI/交互：新增集合卡片栅格（标题、创建时间、描述截断、悬浮高亮），搜索结果提示条、空态创建引导、健康检查侧栏与 API 基址提示；保持按钮/卡片/色板与 M5a 设计系统一致。

### 已知限制 / 后续衔接
- 列表未分页，适用于当前规模；如数据量增大需追加分页参数与 UI 支持。
- Collection 管理等子页面仍为占位，需在 M5c–M5g 继续对接后端接口与 PDF/聊天联动。
- 未执行自动化测试；仅通过代码审阅与交互流程手工演练，需在实际环境中按下方验收步骤走查。
