## OBQA 前端 Markdown 渲染设计文档（M11）

- 依据需求：`docs/dev_log/M11/前端markdown渲染需求文档.md`
- 适用范围：EviQAsys 前端（React），主要涉及 `DocumentChat` / `CollectionChat` 消息渲染层
- 修订记录：v0.1（设计初稿，待评审）

### 1. 背景与现状
- 回答区当前为纯文本渲染（参见 `src/pages/DocumentChat.jsx` 与 `CollectionChat.jsx` 中的 `EvidenceText`），通过正则把 `Evidence#no` 转成按钮，但缺少 Markdown/公式能力，换行在渲染后易被折叠。
- 需求要求在不改后端/映射逻辑的前提下，引入 Markdown + 公式排版，同时保证 Evidence 胶囊在任意 Markdown 节点内可点击触发原有高亮流程。

### 2. 目标与范围
- 引入通用 Markdown 渲染组件，支持 GFM、公式（行内/块级）与换行保留。
- 在 Markdown AST 中识别 `Evidence #数字`（或 `Elem#数字`，并利用 element_id→evidence_no 映射）并渲染为胶囊按钮。
- 与既有 `handleEvidenceSelect` 流程对接，维持 PDF 跳转、高亮与元信息弹窗不变。
- 不在范围：后端协议、PDF viewer 逻辑、evidence 映射算法、UI 体系的全局改版。

### 3. 技术选型
- 渲染核心：`react-markdown`
- Markdown 增强：`remark-gfm`（表格、列表、任务列表等）、`remark-breaks`（保留 LLM 单换行）、`remark-math`（公式解析）
- 公式渲染：`rehype-katex` + `katex/dist/katex.min.css`
- 自定义 tokenizer：基于 remark 插件，将 `Evidence #<num>` / `Elem#<num>` 转为自定义 `evidenceReference` 节点，避免被 Markdown 拆分。


### 4. 组件设计
#### 4.1 新增组件（建议放置 `src/components/MarkdownRenderer.jsx`）
- `MarkdownRenderer`
  - Props：`content: string`、`evidences?: Evidence[]`、`onSelectEvidence?: (evNo:number)=>void`、`className?`
  - 责任：组装 remark/rehype 管道，注入 evidence tokenizer，自定义组件映射（表格、代码块、链接、引用、列表等样式兼容现有 UI），统一渲染入口。
  - 行为：当 `content` 为空返回空态；当解析失败时降级为 `<pre>` 包裹的原文。
- `EvidenceCapsule`
  - 责任：复用 `.evidence-tag` 样式并抽象为独立组件（可放置 `src/components/EvidenceCapsule.jsx` 或内联于 MarkdownRenderer）。
  - 行为：显示 `Evidence #<no>` 文案，点击触发 `onSelectEvidence`。

#### 4.2 remark tokenizer 草案
```js
// 伪代码，实际实现位于 MarkdownRenderer 内
function remarkEvidenceTokenizer(options) {
  const { resolveElementToEvidence } = options
  const regex = /(Evidence|Elem)#(\\d+)/gi
  function locator(value, fromIndex) {
    const match = regex.exec(value.slice(fromIndex))
    return match ? fromIndex + match.index : -1
  }
  function tokenizer(eat, value, silent) {
    const match = regex.exec(value)
    if (!match || match.index !== 0) return
    if (silent) return true
    const [, tokenType, rawNo] = match
    const evNo = tokenType.toLowerCase() === "elem"
      ? resolveElementToEvidence(Number(rawNo))
      : Number(rawNo)
    const node = evNo
      ? { type: "evidenceReference", value: evNo }
      : { type: "text", value: match[0] }
    return eat(match[0])(node)
  }
  tokenizer.locator = locator
  return (tree, file) => { file.data ||= {}; tree.children /* register tokenizer via Parser */ }
}
```
- 通过 `options.resolveElementToEvidence` 使用 turn.evidences 中的映射（现有 `EvidenceText` 已构建 Map，可重用）。
- 生成的 `evidenceReference` 节点在 `react-markdown` 的 `components` 中对应到 `EvidenceCapsule`。
- 根据当前项目情况自行决定： remark v14/v15 的 tokenizer 注册方式（`Parser.prototype.inlineTokenizers` vs `fromMarkdown` 扩展）以适配当前项目依赖版本。

#### 4.3 ReactMarkdown components 映射
- `p`, `ul`, `ol`, `li`, `blockquote`, `table` 等：轻量包裹 className，复用现有 `message__bubble` 色阶。
- `code` / `pre`：保持 monospace，添加水平滚动，避免破版。
- `link`：`target="_blank"` + `rel="noreferrer"`，颜色与品牌色对齐。
- `evidenceReference`：渲染 `EvidenceCapsule`，在表格/列表内也可点击。
- Katex：在 `MarkdownRenderer` 顶层引入 `import "katex/dist/katex.min.css"`。

### 5. 集成方式
- 在 `DocumentChat` / `CollectionChat` 的消息渲染区域，用 `MarkdownRenderer` 替换 `EvidenceText`。
  - 传入 `turn.answer`（或当前字段名）、`turn.evidences`、`onSelectEvidence={(no)=>handleEvidenceSelect(no, turn)}`。
  - 保留 `message-user` / `message-assistant` 容器结构，不改历史样式。
- 复用现有 `handleEvidenceSelect`、高亮状态与弹窗，不新增全局状态。


### 6. 样式与主题
- 继续使用 `.evidence-tag`（见 `src/App.css`），必要时提取为 `.markdown-evidence` 别名，避免未来样式冲突。
- Markdown 默认文字颜色保持 `--color-ink`，标题字号、间距与当前 UI 对齐（可在 `App.css` 添加 `.markdown-body h1/h2/...`）。
- 公式字体使用 Katex 默认样式，颜色继承父级。
- 表格添加横向滚动，避免在小屏破版。

### 7. 性能与安全
- 5k token 文本：`react-markdown` + 轻量插件预计可接受；必要时对 evidence 映射做 `useMemo` 缓存。
- 安全：默认 `skipHtml`；如后续开放 HTML 渲染需增加允许列表和 `rehype-sanitize`。
- 资源：新增依赖 `react-markdown`, `remark-*`, `rehype-katex`, `katex`，需在 package.json 锁定版本并考虑按需分包。

### 8. 边界与降级
- 当 evidence 无映射时，token 退化为普通文本。
- Markdown 解析报错时显示纯文本并写入 console.warn。
- 长行代码块溢出时启用滚动；表格过宽时横向滚动。
- 换行：`remark-breaks` 保留单换行；若影响公式解析需在评审后微调插件顺序。

### 9. 依赖与对外接口
- 输入：`turn.answer` 字符串、`turn.evidences`（含 `evidence_no`、`element_id`、`bbox` 等）。
- 输出：点击 evidence 时调用 `onSelectEvidence(no)`；由父组件决定跳转/高亮。
- 样式依赖：`src/App.css` 现有变量与 `.evidence-tag`。

### 10. 特殊事项
- 根据系统情况自行决定 `react-markdown`、`remark` 的确切版本号及 tokenizer 接口差异需要在安装时确认。
- 不需要在 `DocumentChat` / `CollectionChat` 之外暴露 MarkdownRenderer 供其他页面复用。
