## M5e 开发结果

- 后端接口：新增 `POST /api/collections/{collection_id}/chats` 创建 collection 级聊天；`GET /api/chats/{chat_id}` 返回 chat 元信息、turns（包含 evidences、`answer_with_evidence` 与 `evidence_no_mapping`）；`GET /api/turns/{turn_id}/evidences` 便于按 turn 补充锚点信息；`TurnResponse` 增加 `answer_with_evidence` 字段；默认 LLM 模型改为 `qwen3:235b`。
- Chat 详情解析：基于历史 turn 的 `[Elem#id]` 构建 evidence 编号映射，批量加载元素信息（doc_id/page_no/bbox/level_nav/text_content），每条 turn 返回 evidences 与映射后的答案文本，方便前端直接渲染 `[Evidence#no]`。
- 前端 API 客户端：新增 `createCollectionChat`、`getChatDetail`、`createTurn`、`getTurnEvidences`，沿用 envelope 解析。
- Collection Chat 页面：三栏布局落地，聊天流渲染可点击的 Evidence 标签，发送问题后刷新历史；中栏用 `react-pdf-viewer` + `renderPage` 自定义高亮层，支持文档切换与“打开原始 PDF”；右侧 Sidebar 展示聊天列表、当前 chat 高亮及选中证据元信息联动。
- 样式与依赖：新增聊天气泡/证据标签/PDF 高亮样式，顶栏阶段标记更新为 “M5e collection-chat”；前端依赖加入 `@react-pdf-viewer/core`、`@react-pdf-viewer/page-navigation`、`pdfjs-dist`。

### 已知限制 / 后续衔接
- Evidence 高亮依赖元素的 `bbox_json` 与 `page_no`；缺失时仅展示标签与元信息，不做跳转或绘制。
- `createTurn` 响应未携带 `created_at`，发送后通过刷新 chat detail 获取最新时间戳与顺序。
- `npm install` 提示部分三方依赖弃用/漏洞，未在本次处理，如需可后续 `npm audit fix` 评估。
- ChatHistory / DocumentChat 仍待后续里程碑完善；当前仅完成 Collection Chat 场景。
