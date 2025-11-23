# PDF Viewer 与 Evidence 高亮手动验证清单

## 启动环境
- 后端：`conda activate quest`，运行 `uvicorn EviQAsys.backend.app.main:app --app-dir EviQAsys/backend --reload`，确保返回的 evidence 元数据包含 `document_id/page_index/bbox`。
- 前端：`cd EviQAsys/frontend && npm install`（如未安装依赖），随后执行 `npm run dev`，在浏览器打开 Vite 提示的本地地址。
- 数据：使用真实解析出的文档与 evidence（非 mock）。优先选择已有回答里带 `Evidence#` 标签且包含 bbox 的 turn。

## 核心场景
- Evidence 跳转：在聊天流中点击 `Evidence#` 标签或 chip，确认 PDF 自动切换到对应文档与页面。
- 高亮尺寸：查看命中的矩形是否覆盖正文段落而非“极小点”。若 bbox 为 0-1 归一化坐标，DevTools 控制台应出现“Normalized bbox detected...” 日志。
- 缩放/尺寸适配：调整浏览器窗口尺寸或使用浏览器缩放，确认高亮框随页面同比缩放，边框粗细保持一致（SVG `vector-effect` 生效）。
- 旋转页面：若文档含旋转页面，切换到该页确认高亮仍与内容对齐。
- 文本交互：鼠标悬停/选择文本时应可正常选中，SVG 高亮不拦截事件（pointer-events: none）。
- 缺失 bbox：选择缺少 bbox 的 evidence，右侧卡片应提示“高亮不可用”，PDF 不应残留旧高亮。

## 建议记录
- 记录验证用的 `collection/chat/doc` id、evidence 编号与页码。
- 如发现坐标偏移，截图同时保存控制台日志（bbox 数值与页面原始宽高）以便复现。
