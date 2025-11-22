## M5b 知识库主页实施方案

### 目标与范围
- 依据《开发路线图》M5b DoD，完成“知识库主页”真实列表、搜索/Reset、新建 Collection 弹窗与跳转，覆盖加载、空态、错误态。
- 复用 M5a 的 AppShell/设计系统与请求封装，接通后端 `/api/collections`（GET/POST）并补齐缺失能力（name/description 模糊搜索）。
- 保持路由联动：点击列表行/卡片跳转到 Collection 管理页，同时顶部标签栏与面包屑保持一致。

### 关键设计与接口决策
- **搜索策略：** 后端 `/api/collections` 新增查询参数 `search_field`（`name|description`）+ `keyword` 做 `LIKE` 模糊匹配，返回抽象列表；无搜索参数时返回全部。前端保存“当前查询”状态用于展示 “Searched result” Tag 与 Reset 按钮。
- **创建接口：** 新增 `POST /api/collections` 接收 `{name, description}`，名称必填，描述可空，返回 envelope `{"code":"OK","data":CollectionRead}`。创建成功后重新加载列表并展示 toast。
- **列表展示：** 使用卡片/行样式展示 `name / created_at / description`（描述截断至两行，hover 展开 tooltip 文本），加载态使用“加载中”提示，空态提供创建引导。
- **导航：** 行点击跳往 `/collections/:collectionId`，保持浏览器历史；顶部“+ 新建 Collection”按钮打开 Modal，提交后关闭并刷新列表。

### 前端开发任务拆解
1) **API 层更新**：在 `src/api/client.js` 补充 `listCollections`（支持搜索 query）与 `createCollection`，增强错误提示；保留健康检查与上传接口。
2) **状态与逻辑**：在 `CollectionsHome` 页面实现列表加载、搜索、Reset、创建流程；管理 loading/empty/error toast；记录当前搜索条件以控制 “Searched result” Tag。
3) **UI/交互**：重构主列表为卡片式布局，加入“搜索结果”提示条、Reset 按钮、空态创建引导；Modal 验证必填、提交态禁用按钮；页头/面包屑文案调整为实际功能描述。
4) **导航与提示**：列表行/卡片 click → `useNavigate` 跳转；在 AppLayout 顶栏标记当前里程碑（M5b）。

### 后端开发任务拆解
1) 在 `collections.py` 引入查询参数 `search_field/keyword`，调用仓储的查询函数；返回 envelope `CollectionsEnvelope`。
2) 在仓储层 `CollectionsRepository` 增加 `search_collections`（`LIKE` 模糊匹配、按创建时间倒序），并复用新的路由。
3) 新增 `POST /api/collections` 路由，使用 `CollectionCreate` 校验 payload，调仓储 `create_collection`，处理名称重复/空值错误并返回 envelope。

### 风险与假设
- OceanBase 表已初始化，`collections` 字段包含 `name/description/created_at`，暂不考虑分页；列表规模较小时直接一次性返回。
- 设计稿未提供具体加载骨架，采用简化的“加载中”文本与按钮禁用；如需更丰富骨架可在 M5c 调整。
- 现有其它页面仍为占位，不在本阶段改动。

### 完成判定（对应 DoD）
- `/api/collections` 支持 name/description 搜索与 Reset，回传 envelope，未找到时返回空数组。
- 首页列表真实读取后端并展示 `name/created_at/description`，空/加载态可见；搜索时显示 “Searched result” 标签，Reset 恢复全量。
- 新建 Collection Modal 可提交到后端，成功 toast + 关闭 + 刷新列表，错误可见提示。
- 点击任意卡片跳转到 `/collections/{id}`，顶栏标签状态保持一致。
