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

当前 PDF 渲染技术：前端使用 @react-pdf-viewer/core 搭配 pdfjs-dist worker（pdf.worker.min.js）加载和绘制页面。Viewer 组件内部默认用 canvas 绘制页面（canvasLayer），文本层 (textLayer) 被 CSS 置为透明，仅保留命中区域的自绘高亮。
高亮框实现：自定义 HighlightedPage 用 renderPage 覆写，保留 canvasLayer 与 annotationLayer，并叠加一个绝对定位的 div 容器 .pdf-highlight-layer。对后端返回的 bbox（基于 PDF 坐标）做旋转与缩放换算，然后把每个框渲染为一个 div.pdf-highlight-box（橙色半透明背景 + 实线描边）。
是否使用 SVG：否。高亮是 HTML div 叠加在 canvas 之上（绝对定位），没有用 SVG。

## 自定义高亮实现
- `renderPage` 被重写为 `HighlightedPage`，在默认 `canvasLayer`/`textLayer` 之上叠加 `pdf-highlight-layer`。
- `normalizeBBoxes` 确保后端返回的 bbox 转为二维 `[x0,y0,x1,y1]` 数组；`mapBBoxToRect` 结合 `renderPageProps` 的 `pageWidth/pageHeight/rotation/scale` 做坐标换算，兼容 0/90/180/270 度旋转与放缩。
- `pageHighlights` 只在 `selectedDocId` 与 evidence 的 `document_id` 一致时填充 `{ [pageIndex]: [bbox, ...] }`，避免跨文档误高亮。
- `initialPage` 取自 `pageForHighlight`（点击证据时写入），否则默认 0；同时调用 `pageNavigationPlugin.jumpToPage` 确保 UI 跟随。
- 样式：`.pdf-highlight-box` 使用半透明橙框，`.pdf-viewer` 设置相对定位与滚动，高亮层绝对覆盖。

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
