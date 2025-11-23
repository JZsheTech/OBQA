# M5e 前端 PDF Viewer 与 Evidence 渲染技术路线

## 代码分布
- PDF 预览与证据交互集中在 `EviQAsys/frontend/src/pages/CollectionChat.jsx`。
- 样式与高亮配色定义在 `EviQAsys/frontend/src/App.css`（`pdf-*`、`evidence-*` 相关类）以及 `src/index.css`（变量 `--color-evidence` 等）。
- 后端文件 URL 和聊天/evidence API 调用封装在 `src/api/client.js`。

## PDF Viewer 技术栈与加载逻辑
- 使用 `@react-pdf-viewer/core` 的 `Viewer` + `Worker` 组件，`pageNavigationPlugin` 提供页码跳转，底层 worker 由 `pdfjs-dist/build/pdf.worker.min.js?url` 注入。
- PDF 地址通过 `buildDocumentFileUrl(documentId)` 拼出 `/documents/{id}/file`，并以 `selectedDocId` 作为 `viewerKey` 触发完整重渲染，避免旧状态残留。
- 头部工具栏允许在 `documents` 下拉中切换文档，变更时清空 `pageForHighlight`，保持跳转状态与所选 PDF 一致。
- PDF 文本层被 CSS 设为透明（`.pdf-viewer .rpv-core__text-layer`），仅保留画布层与自定义高亮层，避免与自绘 bbox 叠色。

当前 PDF 渲染技术：前端使用 @react-pdf-viewer/core 搭配 pdfjs-dist worker（pdf.worker.min.js）加载和绘制页面。Viewer 组件内部默认用 canvas 绘制页面（canvasLayer），文本层 (textLayer) 被 CSS 置为透明，自定义高亮层采用 SVG。
高亮框实现：自定义 HighlightedPage 用 renderPage 覆写，保留 canvasLayer 与 annotationLayer，并叠加 SVG 覆盖层 `.pdf-highlight-layer`。SVG 的 `viewBox` 与 `page.view` 的原始宽高一致，`<rect>` 直接使用后端 bbox（必要时在前端检测 0-1 归一化坐标并乘以原始宽高），通过 `vector-effect="non-scaling-stroke"` 保持描边在缩放时不变粗。
是否使用 SVG：是。高亮使用 SVG viewBox 自动映射缩放，无需手动乘以 scale。

## 自定义高亮实现
- `renderPage` 被重写为 `HighlightedPage`，在默认 `canvasLayer`/`textLayer`/`annotationLayer` 之上叠加 SVG `.pdf-highlight-layer`。
- `normalizeBBoxes` 负责将后端 bbox 转为 `[x0,y0,x1,y1]` 数组并保证左右上下顺序；`resolveBBoxToRect` 若检测到 0-1 归一化坐标，则根据 `page.view` 的原始宽高转换为 PDF 点数，不再参与页面缩放计算。
- `pageHighlights` 只在 `selectedDocId` 与 evidence 的 `document_id` 一致时填充 `{ [pageIndex]: [bbox, ...] }`，避免跨文档误高亮。
- `initialPage` 取自 `pageForHighlight`（点击证据时写入），否则默认 0；同时调用 `pageNavigationPlugin.jumpToPage` 确保 UI 跟随。
- 样式：`.evidence-highlight-rect` 使用 SVG 填充与描边，viewBox 自动适配缩放，边框使用 `vector-effect: non-scaling-stroke`。

## Evidence 文本渲染与交互
- 数据源：`getChatDetail(chatId)` 返回 `turns`，每个 turn 携带 `answer_with_evidence`（优先）或 `answer_text` 以及 `evidences`；若本地缺失，点击时会通过 `getTurnEvidences` 补全。
- 解析：`EvidenceText` 先将 `evidences` 构为 `element_id → evidence_no` 映射，再用正则同时识别 `Evidence#` 与 `Elem#` 形式，支持 `[ ... ]` 括号包裹或裸露文本。无法映射的 token 按原文保留。
- 渲染：每个命中的标签输出一个可点击的 `button.evidence-tag`，显示 `Evidence #<no>`，其他文本按片段切分为 `<span>`，避免破坏原有语序。
- 侧边 chips：`turn.evidences` 还会在回答下方生成 `evidence-chip` 行，列出文档与页码，作为另一入口。

## 点击 evidence → PDF 高亮流程
1. 用户点击文本标签或 chip，调用 `handleEvidenceSelect(evNo, turn)`。
2. 优先在当前 turn 的 `evidences` 中寻找指定 `evidence_no`，缺失则请求 `/turns/{id}/evidences` 补充。
3. 写入 `selectedEvidence`，并根据 `document_id`、`page_index`、`bbox`：
   - 更新 `selectedDocId`（保持 PDF 切换到对应文档）；
   - 计算 `pageForHighlight = page_index - 1`，通过 `jumpToPage` 滚动；
   - 通过 `pageHighlights` 将 bbox 映射到高亮层。
4. `SelectedEvidence` 卡片展示元信息与 snippet；若无 bbox，提示“高亮不可用”。

## 选中文档自动回填策略
- 当聊天或 collection 变更时，副作用会先尝试用当前选中证据的 `document_id`；若无，则扫描已有 turn 的 evidences，取首个文档；再无则默认第一个 `documents` 列表项，避免 PDF 区域空白。

## 与《Evidence 渲染规范》的一致性
- 前端不生成编号，而是使用后端返回的 `evidence_no`，通过 `element_id` 映射解析 `[Elem#id]`。
- React key 与逻辑层均以 `element_id` 为准，`evidence_no` 只用于用户可见编号与点击定位。
- 高亮所需的 `document_id/page_index/bbox` 完全依赖后端元信息，前端仅负责坐标换算与呈现。
