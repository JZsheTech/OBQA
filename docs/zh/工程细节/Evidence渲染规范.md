# Evidence 渲染规范（v2 版）

> 本规范约定了 **后端与前端之间关于证据引用（Evidence） 的统一协议**，包括：
>
> * LLM 输出中如何标记证据元素；
> * 后端如何构建 `element_id → evidence_no` 映射并返回；
> * 前端如何渲染带编号的 evidence 标签并高亮 PDF；
> * 历史多轮对话中 Evidence 编号的稳定性要求。
>
> 本规范优先级 **高于** 之前文档中关于 `[Evidence#no]` 直接出现在 answer 文本里的描述。

---

## 1. 核心概念与术语约定

### 1.1 element_id

* 含义：元素在 `elements` 表中的主键 ID（数据库唯一标识）。
* 特性：

  * 全局唯一；
  * 不随聊天历史变化；
  * 是后端和前端在代码层面最重要的“真实身份标识”。
* 用途：

  * React 列表渲染时的 `key`；
  * 高亮 PDF 时定位元素（结合 `doc_id, page_no, bbox`）；
  * 作为 evidence_no 的“真正实体”。

### 1.2 `[Elem#<element_id>]` 原始锚点标签

* 这是 **LLM / DSPy 模块内部** 和 **后端存储** 中使用的统一锚点格式：

  ```text
  [Elem#123], [Elem#45], ...
  ```

* 规范：

  * `<element_id>` 必须是十进制整数，且对应 `elements.id`；
  * 标签仅作为文本中的“占位标记”，所有结构化信息由后端根据 `element_id` 查询；
  * LLM 在回答中引用证据时，**必须使用 `[Elem#<id>]`**，禁止直接输出 `[Evidence#no]`。

### 1.3 evidence_no（展示编号）

* 含义：**在单个 chat 会话内**，按元素首次被引用顺序生成的 **用户可见编号**。
* 特性：

  * 在同一个 `chat_id` 内，对每个 `element_id` 至少有一个唯一的 `evidence_no`；
  * 只在 **展示层** 使用（如 `[Evidence#1]`），**不存入数据库**；
  * 会随着 Chat 历史增加而变化（新增 turn 可能引入新的 evidence_no）。
* 用途：

  * 答案文本前端展示时用于提示用户：

    * “这一条证据是 Evidence #1、#2、#3 ...”
  * 提供点击/hover 交互：用户点击 `[Evidence#3]` 高亮对应 PDF 片段。

> 总结：
>
> * `element_id`：稳定身份，供代码使用；
> * `[Elem#id]`：LLM/后端文本锚点；
> * `evidence_no`：对用户友好的显示编号。

---

## 2. 后端职责与流程

### 2.1 LLM 输出与内部存储

* 后端在调用 LLM / DSPy Answer 模块时，要求其在回答中直接使用 `[Elem#id]`，例如：

  ```text
  The method works as described in the figure [Elem#123]. 
  Similar results are shown in the table [Elem#45].
  ```

* 后端在 `turns` 表中存储的 `answer_text` **保留原始 `[Elem#id]` 标签**，不替换为 `[Evidence#no]`。

### 2.2 构建 element_id → evidence_no 映射

对于某个 `chat_id`：

1. 收集 **该 Chat 历史上所有 turn** 的 `answer_text` 中出现过的 `[Elem#id]`；
2. 按 **turn.order 升序** + **文本出现顺序** 生成一个 `element_id` 的去重列表：

   ```text
   [123, 45, 8, 999, ...]
   ```
3. 依次分配 evidence_no：

   ```text
   element_id 123 → evidence_no 1
   element_id 45  → evidence_no 2
   element_id 8   → evidence_no 3
   ...
   ```

> 规范要求：
>
> * evidence_no 的生成逻辑必须在后端统一实现（例如 `services/mapping/evidence_mapper.py`），前端不得自行生成；
> * evidence_no 不入库存储，每次返回时按上述规则动态计算。

### 2.3 API 返回结构（推荐形态）

后端向前端返回某个 turn 时，**推荐**的 JSON 结构为：

```jsonc
{
  "turn_id": 17,
  "chat_id": 3,
  "question": "What is the main contribution of the paper?",
  "answer_text": "The method works as described in Fig. 3 [Elem#123], and ... [Elem#45].",
  "evidences": [
    {
      "element_id": 123,
      "evidence_no": 1,
      "doc_id": 5,
      "page_no": 10,
      "bbox": [100, 120, 250, 300],
      "elem_type": "image",
      "level_nav": "1. Introduction > 1.1 GNN",
      "evidence_title": "[doc=Paper Title] [page_no=10] [nav=1. Introduction > 1.1 GNN]",
      "text_snippet": "Figure 3. Overall architecture ..."  // 可选：截断后的 text_content 预览
    },
    {
      "element_id": 45,
      "evidence_no": 2,
      "doc_id": 5,
      "page_no": 14,
      "bbox": [40, 80, 200, 240],
      "elem_type": "table",
      "level_nav": "3. Experiments > 3.2 Main results",
      "evidence_title": "[doc=Paper Title] [page_no=14] [nav=3. Experiments > 3.2 Main results]",
      "text_snippet": "Table 2. Main results ..."          // 可选
    }
  ]
}
```

说明：

* `answer_text` 中 **仍然是 `[Elem#id]`**；
* `evidences` 数组中的每一项：

  * `element_id`：用于前端渲染 key + 高亮定位；
  * `evidence_no`：用于前端显示“Evidence #编号”，以及替换文本中的 `[Elem#id]`；
  * `doc_id` / `page_no` / `bbox` / `elem_type`：前端高亮 PDF 所需数据；
  * `level_nav` / `evidence_title`：用于展示“文档标题 + 页码 + 章节路径”的归属信息；
  * 可选字段：`text_snippet` 等，对前端 UX 有帮助但非必要。

> 注意：
> 若前端一次性请求整个 chat 的对话列表，后端可在列表级别返回一个合并后的全局 `evidences` 映射（包含整个 chat 的所有元素），具体 API 设计可在 `service_interface_use.md` 中另外定义。

---

## 3. 前端渲染规范（React 视角）

### 3.1 React 列表渲染 key 必须使用 element_id

当前端渲染 evidence 列表（例如侧边栏、弹出列表）时：

```jsx
{evidences.map(ev => (
  <EvidenceItem
    key={ev.element_id}       // ✅ 使用 element_id 作为 React key
    evidenceNo={ev.evidence_no}
    elementId={ev.element_id}
    title={ev.evidence_title}
    ...
  />
))}
```

**禁止** 使用 `evidence_no` 作为 key，例如以下是 ❌ 反例：

```jsx
// ❌ 不推荐：
key={ev.evidence_no}
```

原因：

* evidence_no 在 chat 历史扩展时可能变化（即便同一元素），不稳定；
* element_id 来自数据库主键，稳定不变，是正确的 key 选择。

### 3.2 文本中 `[Elem#id]` → UI 中 `[Evidence#no]` 的替换逻辑

前端收到的 `answer_text` 形如：

```text
"... as shown in Fig. 3 [Elem#123], and further in [Elem#45]."
```

前端应：

1. 对 `answer_text` 做一次 **纯前端解析**，找到所有 `[Elem#(\d+)]`；
2. 使用 evidences 数组构建本轮的 `element_id → evidence_no` 映射字典：

   ```ts
   const elemIdToNo: Record<number, number> = {};
   evidences.forEach(ev => { elemIdToNo[ev.element_id] = ev.evidence_no; });
   ```
3. 按如下规则替换为可点击高亮的 UI 组件，例如伪代码：

   ```jsx
   // 伪代码：将 "xxx [Elem#123] yyy" 转为包含 <EvidenceTag no=1 elemId=123 />
   renderAnswer(answer_text, evidences) {
     // parse text into segments + tags
     // replace [Elem#id] with <EvidenceTag ... />
   }
   ```

渲染出来的效果示例：

```text
... as shown in Fig. 3 [Evidence #1], and further in [Evidence #2].
```

其中 `[Evidence #1]` / `[Evidence #2]`：

* 文本上展示 evidence_no；
* 内部绑定 element_id，用于点击时高亮 PDF。

### 3.3 点击 Evidence 标签 → 高亮 PDF

渲染 `[Evidence #k]` 标签时组件内应包含：

* `evidence_no`（展示用）
* `element_id`（逻辑用）

交互流程（建议）：

1. 用户点击 `[Evidence #k]`；
2. 前端通过 `evidence_no` 在 evidences 数组中找到对应对象 `ev`：

   ```ts
   const ev = evidences.find(e => e.evidence_no === k);
   ```
3. 取出：

   * `doc_id`
   * `page_no`
   * `bbox`
4. 通知 PDF Viewer 跳转到对应文档、页码，并在 `bbox` 框内做高亮。

> ⚠️ 重点：
>
> * 实际定位/高亮逻辑由前端负责（PDF viewer 内部实现），**后端只需提供 bbox 等元信息**；
> * 任意 UI 形态（侧边栏列表、tooltip、下划线、mask 层）都需遵守：**点击/hover 最终是用 element_id 去定位**。

---

## 4. 多轮对话与 Evidence 稳定性

### 4.1 chat 维度的 evidence_no 全局性

* evidence_no 的定义：
  “**在单个 chat 内**，按 element 第一次被引用的顺序编号”。

* 这意味着：

  * 对于同一个 `chat_id`，无论是第 1 轮回答还是第 10 轮回答，只要引用的是同一个 `element_id=123`，它的 `evidence_no` 在同一轮计算中应该一致（例如都为 `1`）；
  * 当新增新的 turn 引入了新的 element 时，新元素才会获得新的编号（3、4、5……）。
  * 这一特性在后端首次加载该chat时从每轮turn的answer文本中动态计算得到。

### 4.2 历史答案文本不做后端重写

* 历史 `answer_text` 中保留 `[Elem#id]`：

  * 不会因为 evidence_no 的变化而修改历史文本；
  * evidence_no 完全由后端动态计算得到（通过当前后端给出的映射）。
  * `turn2element` 写入范围：只为“答案文本里真实出现的 `[Elem#id]`”写记录，而不为未被引用但参与上下文的候选元素写入.

* 若需要在聊天列表 UI 中显示“[Evidence #no]”：

  * 一律在前端渲染阶段通过 `[Elem#id]` + 统一映射完成；
  * 后端无需对历史文本做字符串替换。

---

## 5. 与现有文档的对齐与迁移说明

### 5.1 与《数据模型.md》的关系

* `elements` 表：

  * 本规范使用其中的 `id`（即 element_id）、`doc_id`、`page_no`、`bbox_json`、`elem_type`、`level_nav` 等字段；
* `turns` 表：

  * `answer_text` 字段现在**明确要求**存储带 `[Elem#id]` 的原始文本；
* `turn2element` 表：

  * 仍然作为 turn 与 elements 的桥表使用，不存 `evidence_no`；
  * evidence_no 每次响应 API 时按 chat 维度动态生成。

### 5.2 与《多模态论文问答系统设计文档.md》的关系

* 原文中若有“后端将 `[Elem#id]` 替换为 `[Evidence#no]` 再返回前端”的表述，**以本规范为准进行修订**：

  * **内部存储 / LLM 输出**：使用 `[Elem#id]`；
  * **API 返回 answer_text**：仍为 `[Elem#id]`；
  * **API 附带 evidences 数组**：携带 `element_id` + `evidence_no` + 高亮信息（`doc_id/page_no/elem_type/bbox/level_nav/evidence_title` 等）；
  * **前端负责将 `[Elem#id]` 渲染成可视的 `[Evidence #no]` 组件。

### 5.3 与《开发路线图.md》的关系

* M4 阶段涉及的 Evidence 功能实现，应遵守：

  * evidence_no 只存在于：

    * API response；
    * 前端展示；
  * 后端：

    * 实现 element_id → evidence_no 的生成逻辑；
    * 实现返回 evidences 数组（至少包含 element_id、evidence_no、doc_id、page_no、elem_type、bbox、level_nav、evidence_title 等字段）；
  * 前端：

    * 用 element_id 作为 React key；
    * 用 evidence_no 作为用户可见编号；
    * 实现 `[Elem#id]` → `EvidenceTag` 的替换逻辑。

---

## 6. 给 coder 的简短操作性总结

> 实现/修改代码时，请遵守以下四条硬性规则：

1. **LLM / DSPy 的回答中，证据锚点必须是 `[Elem#<element_id>]`，不得输出 `[Evidence#no]`。**
2. **后端存储 `turns.answer_text` 时，保留原始 `[Elem#id]`。不在 DB 里写入 evidence_no。**
3. **每次构造 API 响应时，后端负责：**

   * 统计该 chat 内所有被引用的 `element_id`；
   * 生成 `element_id → evidence_no` 映射；
   * 在响应体中附带 `evidences` 数组（含 element_id、evidence_no、doc_id、page_no、elem_type、bbox、level_nav、evidence_title 等）。
4. **前端所有 React 列表的 key 使用 `element_id`；**

   * 将 `answer_text` 中的 `[Elem#id]` 替换为带 `evidence_no + element_id` 的 UI 组件；
   * 用 `element_id` + `doc_id/page_no/bbox` 去高亮 PDF。
