
M4_refactor_doc.md

关于evidence锚点存储机制的修改指南

本计划完全基于你刚刚确定的架构方向：

> **数据库只存 turn2element，不再存 evidence_no；
> evidence_no 在返回前端时按 element 首次出现顺序动态生成；
> LLM 只引用 [Elem#element_id]；
> 前端收到答案后是 [Evidence#no]（已转换好的）。**

以下内容会精准告诉 coder：

* 哪些文档要改
* 哪些段落要改
* 哪些字段要删
* 哪些新说明要加
* 哪些流程图/交互逻辑要更新
* 哪些代码层面需要调整
* 对应数据库 DDL 如何修改
* 对应 API 返回结构如何修改

让 coder 可以“一条龙执行”，无需推理。

---

# 📘 **《PaperQA 系统文档和数据模型修改计划（M4 Evidence 清理与统一）》**

以下文档将被更新：

1. 《多模态论文问答系统设计文档.md》
2. 《数据模型.md》
3. 《前后端交互逻辑设计.md》
4. 《开发路线图.md》（M4/M5 部分）
5. 后端代码框架中涉及 evidence_no 的说明

全部统一为以下新规则：

> **系统内部不再使用 evidence_no 存储；
> evidence_no 是展示层编号，只在 API 输出前动态生成。
> turn2evidence 表更名为 turn2element 表，并移除 evidence_no 字段。
> LLM 锚点统一采用 [Elem#element_id] 格式。**

---

# 🚀 **第 1 部分：数据库 DDL 修改计划**

## 1.1 删除 evidence_no，修改表名 turn2element

### **当前结构（需要改动）**

来自数据模型文件：

```
turn2evidence(
    chat_id BIGINT,
    turn_id BIGINT,
    turn_order INT,
    evidence_no INT,
    element_id BIGINT,
    created_at DATETIME
)
PRIMARY KEY(chat_id, evidence_no)
```

### ❌ 需要修改为：

```
-- 新表名：
turn2element (

    chat_id BIGINT NOT NULL,
    turn_id BIGINT NOT NULL,
    turn_order INT NOT NULL,

    -- 此处不再有 evidence_no
    element_id BIGINT NOT NULL,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (chat_id, turn_id, element_id),

    FOREIGN KEY(chat_id) REFERENCES chats(id) ON DELETE CASCADE,
    FOREIGN KEY(turn_id) REFERENCES turns(id) ON DELETE CASCADE,
    FOREIGN KEY(element_id) REFERENCES elements(id) ON DELETE CASCADE
)
```

### **字段说明（要加入文档）**

* **不存 evidence_no**
* **按 turn_order 记录证据首次出现顺序**
* 主键可使用 `(chat_id, turn_id, element_id)`
* 允许多轮引用同一个 element_id（但同一 turn 中不会重复）

---

# 🚀 **第 2 部分：AI 锚点协议修改计划**

## 2.1 DSPy / LLM 输出格式规范（要加入设计文档 M4）

替换原规则（[Evidence#no]），新增：

---

### **LLM 只能输出如下格式：**

```
[Elem#<element_id>]
```

例如：

```
As shown in [Elem#1542], the reward model is defined as...
```

---

### **禁止：**

* `[Evidence#no]`（禁止由 LLM 生成）
* 自己编造的 element_id（不在候选列表中）

---

### **提示词中必须加入：**

```
You must cite evidence using the form [Elem#<element_id>].
Only use element_id values from the provided candidate list.
Do NOT generate numbering (Evidence#no). Numbering will be handled by the system.
```

---

# 🚀 **第 3 部分：Evidence_no 的动态生成逻辑（API 层）**

要加入文档中的 “问答流程(M4)” 部分。

---

## 3.1 evidence_no 的生成原则

```
evidence_no = 元素在这个 chat 中首次出现的顺序编号（从 1 开始）
```

由后端动态构建映射：

```
chat_id → [element_id 的首次出现顺序]
```

### 映射示例：

| element_id | 首次出现 turn | evidence_no  |
| ---------- | --------- | ------------ |
| 1542       | turn 1    | 1            |
| 2001       | turn 1    | 2            |
| 1788       | turn 2    | 3            |
| 1542       | turn 3    | 1（重复元素不重新编号） |

---

## 3.2 API 返回前端时必须做两件事：

### **(1) 替换答案文本**

从：

```
... as shown in [Elem#1542] ...
```

替换为：

```
... as shown in [Evidence#1] ...
```

### **(2) Evidence API 返回结构保持不变**

返回：

```
[
  {
    evidence_no: 1,
    element_id: 1542,
    doc_id: 5,
    page_no: 12,
    bbox: [...],
    snippet: "..."
  }, ...
]
```

只是 evidence_no 改为动态生成。

---

# 🚀 **第 4 部分：后端代码需修改的模块**

## 4.1 模块需修改（添加到设计文档和路线图）

| 模块                                    | 变更内容                                             |
| ------------------------------------- | ------------------------------------------------ |
| `repositories/t2e_repo.py`            | 重命名为 `t2element_repo.py`，移除 evidence_no          |
| `services/qa_flow.py`                 | LLM 输出解析从 `[Evidence#no]` 改为 `[Elem#element_id]` |
| `services/mapping/evidence_mapper.py` | 新增：element_id → evidence_no 的动态生成器               |
| `services/answer/postprocess.py`      | 替换 `[Elem#id]` → `[Evidence#no]`                 |
| `api/chats/{chat_id}/turns`           | 写入 turn2element；返回 answer 时执行替换                  |
| `api/turns/{turn_id}/evidences`       | 动态生成 evidence_no 并返回                             |

---

# 🚀 **第 5 部分：前后端接口（交互逻辑）需要更新的内容**

修改文件：前后端交互逻辑设计.md
参考：

## 5.1 新规则加入

* 前端永远只收到 `[Evidence#no]`，不会看到 `[Elem#id]`
* 后端内部计算 evidence_no，不需要由前端参与
* PDF 高亮依据 element_id 获取 bbox/page_no

### GET /api/turns/{turn_id}/evidences 新返回结构：

```
{
  code:"OK",
  data: {
    evidences: [
      {
        evidence_no: 1,
        element_id: 1542,
        doc_id: ...,
        page_no: ...,
        bbox: ...
      },
      ...
    ]
  }
}
```

---

# 🚀 **第 6 部分：开发路线图（M4 修改）**

需要更新文件：开发路线图.md
参考：

### 原 M4 步骤中的“写 turn2evidence 表” → 改为：

1. 解析 LLM 输出中出现的 `[Elem#element_id]`
2. 写入 turn2element（每个 element_id 一条记录）
3. 查询 chat 历史构建 evidence_no 映射
4. 替换答案内的 `[Elem#id]` 为 `[Evidence#no]`
5. 返回 answer 给前端
6. GET evidences 时动态返回 evidence_no

### 原文中的 evidence_no 说明应全部删除或替换为上述规则

---

# 🚀 **第 7 部分：文档修改 checklist（给 coder 用）**

这是 coder 直接可执行的 checklist：

### 📌 **数据库模型修改**

* [ ] 删除旧表 turn2evidence
* [ ] 新建 turn2element 表（无 evidence_no）
* [ ] 修改相关外键与主键（按文档）
* [ ] 更新所有仓储层 CRUD 代码

---

### 📌 **后端服务修改**

* [ ] 修改 QA Flow，使 LLM 输出 [Elem#id]
* [ ] 新增 evidence_no 动态生成器
* [ ] 替换答案中的锚点
* [ ] GET /evidences 时输出 evidence_no
* [ ] 去掉所有 evidence_no 写库逻辑
* [ ] 更新路由文档注释

---

### 📌 **设计文档需要更新**

* [ ] 数据模型文档（删 evidence_no，表更名，字段说明）
* [ ] 系统设计文档（更新 M4 流程、锚点规则、替换逻辑）
* [ ] 前后端交互逻辑（统一锚点格式说明）
* [ ] 开发路线图（更新 M4）

---

### 📌 **前端**

* [ ] 不再解析 [Elem#id]，只处理 [Evidence#no]
* [ ] 点击 evidence_no 时调用 GET /turns/{turn_id}/evidences
* [ ] 用 element_id 定位元素 bbox/page_no

---

# 🎉 **最终总结：文档/数据库修改方向**

✔ turn2evidence → turn2element
✔ 移除 evidence_no（不再存库）
✔ evidence_no 仅在 API 最后一步生成
✔ LLM 锚点统一 [Elem#element_id]
✔ 前端只看到 [Evidence#no]（展示编号）
✔ 文档中涉及 evidence_no 的所有部分需要重写

由于数据库的turn2evidence表要修改成turn2element，我需要你同时修改对应的python代码
并且给出一个一键重置数据库中所有表的脚本(即删除所有的表然后再重建)
