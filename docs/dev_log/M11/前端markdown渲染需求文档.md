技术栈：
使用 react-markdown 作为渲染框架，配合 remark-gfm / remark-math / rehype-katex 支持 Markdown 和公式，并实现一个自定义 remark tokenizer 将“Evidence #数字”识别为 evidence 节点，再在 react-markdown 的 components 中渲染成可点击胶囊组件。



# 📘 **《OBQA 前端 Markdown 渲染 + Evidence 胶囊显示 功能需求文档（精简版）》**

版本：v1.0
角色：PM（ChatGPT）
执行者：本地 Cursor AI coder
范围：OBQA / EviQAsys 前端（React）

---

# 1. 🎯 功能背景

目前系统的回答区域是纯文本，缺乏排版能力，阅读体验较差。
同时，回答中包含大量的 Evidence 引用（如 `Evidence #35`），这些引用在前端需呈现为可点击胶囊标签，用于跳转和高亮 PDF 页面中的对应元素。

需要：

* 引入 Markdown 渲染能力（支持标题、列表、表格、代码块、链接等）
* 支持数学公式（`$...$` 与 `$$...$$`）
* 在 Markdown 中保持 Evidence 标签的解析与可点击胶囊展示，不被 Markdown 渲染破坏
* 点击 Evidence 胶囊后继续调用现有系统逻辑实现 PDF viewer 的跳转和高亮
* 前端应当正确保留LLM输出的换行，不要把所有内容挤到一起显示。

---

# 2. 📦 功能目标

## 2.1 Markdown 渲染

* 回答区域采用 Markdown 渲染方式显示文本。
* 支持常用排版结构：标题、列表、引用、表格、内联代码、代码块等。
* 支持数学公式（行内与块级）。

## 2.2 Evidence 引用渲染

* 对答案文本中的 `Evidence #数字` 进行识别。
* 渲染时替换为“蓝色胶囊标签”，样式与当前系统保持一致。
* 胶囊标签在 Markdown 中的任意位置（段落内、列表内、表格单元格内）均需正常显示。
* Evidence 标签不可被 Markdown 格式破坏或转义为纯文本。

## 2.3 交互行为

* 用户点击 Evidence 胶囊 → 触发父组件提供的回调方法。
* 回调方法会继续调用现有逻辑：跳转至 PDF viewer 对应页并高亮 element。
* Evidence 与 element 映射逻辑保持当前系统实现方式，不需要改动。

---

# 3. 🔌 兼容性要求

* Markdown 渲染只影响展示层 **不改变 answer 文本内容本身**。
* Evidence 标签的识别规则需足够稳定，不应误解析普通文本。
* Markdown 与 Evidence 渲染需共存，不互相破坏。
* 渲染性能需满足长文本（约 5k token）无明显卡顿。

---

# 4. 📐 研发边界

## 不在本次 scope 内：

* 修改 AnswerAgent 的输出格式
* 修改 evidence_no 与 element_id 的映射逻辑
* 修改 PDF viewer 高亮逻辑
* 使用 MDX 或替换现有 UI 框架

## 在 scope 内：

* 引入 Markdown 渲染能力
* 增加 Evidence 的 Markdown 嵌入式渲染支持
* 保持 UI 风格一致

---

# 5. 🧩 交付物

Coder 需最终交付：

1. 一个 Markdown 渲染组件（单个入口）
2. 一个可以被 Markdown 调用的 Evidence 胶囊组件
3. 一个机制：识别 `Evidence #数字` 并替换为 Evidence 组件
4. 在 Answer 展示区域集成新的 Markdown 渲染流程
5. 至少两段效果截图（包含公式 + Evidence 混合渲染）

---

# 6. 📝 验收标准（产品维度）

* Markdown 格式显示正确，美观一致，无破版情况。
* 公式排版正确，块级与行内均不报错。
* Evidence 标签在 Markdown 内显示为胶囊，不被破坏。
* 点击 Evidence 标签能正常跳转与高亮对应元素。
* 与当前 UI 风格保持一致（视觉与交互行为不改变）。

---

# 7. 🧭 备注

该功能为展示层改造，不影响系统整体架构。
所有 Evidence 的逻辑延续当前系统，不涉及数据库或后端变更。

