# M11 前端 Markdown 渲染升级计划

- 范围：EviQAsys 前端聊天消息展示层（DocumentChat / CollectionChat）
- 目标：上线 Markdown+公式渲染与 Evidence 胶囊共存能力，保持现有高亮交互不变

## 1. 里程碑（划分阶段）
- M1（D1）：引入依赖（react-markdown、remark-gfm、remark-breaks、remark-math、rehype-katex、katex），完成基础渲染 Demo。
- M2（D2）：完成 Evidence tokenizer + EvidenceCapsule 组件，支持 element_id→evidence_no 映射。
- M3（D3）：接入 `DocumentChat` / `CollectionChat`，替换 `EvidenceText`，通过 onSelectEvidence 触发原高亮流程。
- M4（D4）：样式细化（表格、代码块、胶囊对比度）、Katex 样式引入，长文本性能自检（5k tokens）。
- M5（D4-D5）：手动验证、截图归档、设计/PM 评审，准备发布说明。


## 2. 任务拆分
1) 依赖与基础设施
   - 更新 `package.json` & lock；添加 `katex/dist/katex.min.css` 引入点。
   - 建立 `src/components/MarkdownRenderer.jsx`（或同级命名）与 `EvidenceCapsule`。
2) Markdown + Evidence 管道
   - remark 插件：实现 `Evidence|Elem#<num>` tokenizer，暴露 `resolveElementToEvidence`。
   - ReactMarkdown components：表格/代码/链接/blockquote 样式适配；`evidenceReference` 映射到胶囊。
   - 换行处理：接入 `remark-breaks`，确认对公式解析无副作用。
3) 页面集成
   - `DocumentChat`：用 MarkdownRenderer 替换 `EvidenceText`，保持 message 容器结构，复用 `handleEvidenceSelect`。
   - `CollectionChat`：同上，并确认跨文档 evidence 切换后页面选择逻辑正常。
   - `PdfHighlightDemo` 页面可以直接删除。
4) 样式与 UX
   - 复用 `.evidence-tag`，必要时新增 `.markdown-body` 作用域避免污染。
   - 表格/代码块滚动、防破版；链接 hover/visited 颜色。
   - 公式字体与行高检查。
5) 验证与交付
   - 手动测试脚本（命令行触发）：使用真实回答样例，覆盖“纯 Markdown”“公式”“表格+Evidence 混排”“长文本”。
   - 截图 2+（含公式、Evidence 混排）纳入 PR 说明。
   - 文档更新：同步 `docs/dev_log/M11/前端markdown渲染设计文档.md` 与变更摘要。

## 3. 风险与缓解
- remark tokenizer 版本差异导致注册失败 → 预先确认版本，必要时切换到 mdast 自定义节点扩展。
- Evidence 映射缺失（Elem#id 无对应 evidence_no） → 降级为普通文本并打印警告，避免阻断渲染。
- Katex 样式冲突或体积影响 → 作用域限定 + 按需引入，评估 bundle 体积；。
- 长文性能问题 → 观察渲染耗时，必要时拆分 message 或懒加载渲染。

## 4. 验证计划（手动）
- 数据：使用真实聊天记录（包含 `Evidence#`、公式、表格），不可使用 mock。
- 步骤：
  - 运行前端 `npm run dev`，打开 DocumentChat / CollectionChat。
  - 样例 1：输入含标题/列表/链接的 Markdown，检查换行与列表样式。
  - 样例 2：输入 `$a^2+b^2=c^2$` 与 `$$\int_0^1 x dx$$`，确认 Katex 渲染。
  - 样例 3：文本中多处 `Evidence #35`、`[Evidence#12]`，在表格/列表内点击胶囊，确认跳转/高亮与弹窗。
  - 样例 4：长文本（≥5k tokens），观察滚动与交互是否卡顿。
- 记录：截屏、控制台警告/错误收集，形成 PR 佐证。

## 5. 交付物清单
- 代码：MarkdownRenderer + EvidenceCapsule + 集成改动。
- 样式：Katex CSS 引入、必要的 Markdown 作用域样式。
- 文档：设计文档（本次更新）、升级计划（本文）、PR 说明与截图。
- 验证：手动测试日志/截图。
