## M5e Collection Chat 页面实施方案（Chat + 多文档 PDF + Sidebar）

### 目标与范围
- 依据《开发路线图》M5e DoD 落地 Collection Chat 三栏页面：左聊天流（含 `[Evidence#no]` 标签）、中间多文档 PDF Viewer（可切换 doc 并按 bbox 高亮）、右侧 Sidebar 聊天列表。
- 打通 chat 生命周期：创建/切换 collection 级 chat，加载历史，提问并渲染 evidences，高亮跳转 PDF。
- 后端补齐 chat 相关 API（创建、详情含 evidences、turn evidences），默认 LLM 模型切换为 `x-ai/grok-4.1-fast`（OpenRouter，原 `qwen3:235b` 可通过环境变量指定）。

### 关键设计与接口决策
- **Chat 创建与加载**：新增 `POST /api/collections/{collection_id}/chats`（payload: title 可选，type 固定 collection），返回 `ChatRead`。新增 `GET /api/chats/{chat_id}` 返回 chat 元信息 + turns 列表（id/order/user_question/answer_text/raw_created_at），同时提供 `evidence_no_mapping`（element_id→evidence_no）、每个 turn 的 `evidences`（含 bbox/page_index/snippet/title/elem_type/document_id）以及 `answer_with_evidence`（将 `[Elem#id]` 替换为 `[Evidence#no]` 便于前端渲染）。缺失 chat 返回 404。
- **Turn 证据查询**：新增 `GET /api/turns/{turn_id}/evidences`，基于所在 chat 的历史顺序重建 evidence_no，并返回 `evidences` 列表 + mapping，便于前端点击 tag 时刷新高亮信息。
- **LLM 默认模型**：`LLMSettings.model` 默认改为 `x-ai/grok-4.1-fast`（OpenRouter），保持其余配置不变，仍支持通过环境变量切换回 Ollama。
- **PDF Viewer & bbox 渲染**：前端使用 `@react-pdf-viewer/core` 的 `renderPage` 自定义层，读取 RenderPageProps 的 `scale/rotation` 与 page size，将 MinerU 存储的 bbox（[x0,y0,x1,y1]，PDF 左下坐标）按 `draw_layout_minerU_py/cal_canvas_rect` 逻辑转换为 CSS 绝对定位：翻转 y 轴、处理 0/90/180/270 旋转、乘以缩放系数后绘制半透明高亮层。
- **交互行为**：点击聊天中的 `[Evidence#no]` tag → 选中对应 evidence，若有 bbox 则 viewer 跳转至 `page_index-1` 并闪烁高亮；无 bbox 时在右侧给出降级提示。文档下拉来自 `/api/collections/{id}/documents`，默认选第一条或 evidence 所属文档。

### 后端任务拆解
1) 路由与 schemas：在 `api/routes/chats.py` 中新增 create_chat、get_chat_detail、get_turn_evidences；补充 Pydantic 模型（ChatDetail/TurnWithEvidence/EvidencesEnvelope）。复用 `evidence_mapper` 计算 mapping，并提供 `answer_with_evidence` 字段。
2) 仓储复用：使用 `ChatsRepository` 检查 collection_id/存在性，`TurnsRepository.list_by_chat` 加载历史，`Turn2ElementRepository.list_by_chat`/`ElementsRepository.list_by_ids` 获取元素元数据与 bbox。保持 envelope `{code,data}`。
3) 配置：更新 `env_setting.py` 默认 `LLM_MODEL_NAME = x-ai/grok-4.1-fast`，`LLM_API_BASE` 默认走 `https://openrouter.ai/api/v1`。

### 前端任务拆解
1) 依赖与 API 客户端：安装 `@react-pdf-viewer/core`（以及必要样式），在 `api/client.js` 增加 `createCollectionChat`, `getChatDetail`, `getTurnEvidences`, `createTurn`；补充解析 `evidence_no_mapping`。保留现有 envelope 处理。
2) 布局与状态：重写 `pages/CollectionChat.jsx` 为三栏布局（chat panel + pdf viewer + sidebar），状态包含 `chat`, `turns`, `chatList`, `documents`, `selectedDocId`, `selectedEvidence`, `loading`/`sending`/`error`。顶部按钮支持新建聊天（调用 createCollectionChat 成功后跳转）。
3) 聊天渲染：聊天列表按 order 时间顺序渲染气泡；回答文本用 mapping 将 `[Elem#id]` 渲染为可点击 `[Evidence#no]` tag，点击时设置 `selectedEvidence` 并若需要调用 `getTurnEvidences`（兜底刷新）。输入框+发送按钮调用 `createTurn` 追加流，失败时 toast + 标记气泡状态。
4) PDF Viewer：基于 `Viewer` + `renderPage` 绘制高亮层；doc 下拉切换 `fileUrl=buildDocumentFileUrl(docId)`；在 `selectedEvidence` 变化时跳转到对应页（pageNavigationPlugin/jumpToPage）并只渲染当前页 bbox。缺失 bbox 时在右侧提示。
5) Sidebar：右列展示 collection 级聊天列表（`/api/collections/{id}/chats`），当前 chat 高亮，可点击切换；同时展示当前选中 evidence 的 meta（doc/page/type/snippet）供确认。

### 风险与假设
- MinerU bbox 坐标假定与 `cal_canvas_rect` 相同（左下为原点，单位与 page 宽高一致）；若实际数据存在旋转信息缺失，高亮可能有偏移，需在后续验收时以真实 PDF 校正。
- OceanBase/元素数据必须包含 `page_no` 与 `bbox_json`；若缺失，则仅显示 Evidence tag 不跳转 PDF。
- Chat 表当前可能为空，新建聊天与提问依赖后端 QA 流已打通（M4 已验收）；若向量化未完成，回答可能缺少 evidences。

### 完成判定（对应 DoD）
- `POST /api/collections/{collection_id}/chats` 可创建 chat 并返回 envelope，`GET /api/chats/{chat_id}` 返回 turns+evidence_no_mapping+answer_with_evidence，`GET /api/turns/{turn_id}/evidences` 可回传该 turn 的 evidences。
- Collection Chat 页面三栏布局可加载真实聊天历史，发送问题后展示包含 `[Evidence#no]` 的回答 tag。
- 文档下拉可切换 PDF，点击 evidence tag 能跳转到对应页并显示半透明 bbox 高亮（无 bbox 时有提示），Sidebar 能切换 chat。
- LLM 默认模型已切换为 `x-ai/grok-4.1-fast`（OpenRouter）。***
