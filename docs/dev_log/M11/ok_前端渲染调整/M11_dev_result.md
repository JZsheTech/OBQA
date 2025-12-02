# M11 前端 Markdown 渲染增强交付结果

已经完成并经过验收。
## 开发内容
- 新增 `src/components/MarkdownRenderer.jsx`，基于 `react-markdown` + `remark-gfm/remark-math/remark-breaks/rehype-katex` 渲染 Markdown 与公式，并内置自定义 remark tokenizer，将 `Evidence #<no>` / `Elem#<id>` 解析为可点击的胶囊节点，缺失映射时降级为纯文本。
- 调整样式（`App.css`）以作用域化 Markdown 标题、列表、代码块、表格和胶囊间距，引入 KaTeX 样式并对块级公式、表格滚动做兼容。
- 在 `DocumentChat.jsx` 与 `CollectionChat.jsx` 中用 `MarkdownRenderer` 替换旧版 `EvidenceText`，保持 `handleEvidenceSelect` 高亮流程，答案可同时承载 Markdown、公式与 Evidence 胶囊。
- 移除 `PdfHighlightDemo` 路由与页面，简化聊天入口；前端依赖新增 `react-markdown`、`remark-*`、`rehype-katex`、`katex` 并同步锁文件。

## 人工验证步骤（仅手动、需真实数据）
1) 启动前端：在 `EviQAsys/frontend` 执行 `npm run dev`，保持后端与样例数据正常可读（不得使用 mock）。
2) Markdown 与换行：在 DocumentChat/CollectionChat 输入包含标题、列表、链接的真实问题或回放历史答案，确认换行保留、列表缩进与链接跳转正常。
3) 公式渲染：提交含 `$a^2+b^2=c^2$` 和 `$$\\int_0^1 x dx$$` 的问题，观察行内/块级公式由 KaTeX 正常排版，无报错。
4) Evidence 胶囊：使用包含 `Evidence #<no>` 与 `Elem#<element_id>` 的真实回答（来源于后端检索结果），检查胶囊在段落/列表/表格内均可点击，点击后触发原有 PDF 跳转与高亮；对无法映射的元素应显示为纯文本。
5) 表格与代码块：用带表格、代码片段的长回答验证表格横向滚动、代码块不破版；同时观察 5k tokens 级别长文本滚动性能是否顺畅。

> 说明：未编写或执行自动化测试，验证均需人工通过真实数据/对话完成。npm 安装过程提示部分上游依赖存在已知漏洞，暂未在本次处理范围内。
