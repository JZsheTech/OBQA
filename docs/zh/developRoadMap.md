
# 🔧 PaperEvidenceQA RoadMap（后端优先版）

## **Stage 0｜系统基础与数据表落地**

**目标**：系统能启动、OceanBase 表结构稳定、FastAPI 路由通。
**任务**

* 搭建 FastAPI 项目骨架：`/collections /documents /elements /chats /turns /search` 路由。
* OceanBase 数据库初始化脚本：建好

  * 基础表（collections、documents、elements、chats、turns）
  * 桥表（evidence2element，唯一约束 `(chat_id, evidence_no)`）。
* 封装数据库访问层（DAO / SQLAlchemy Core 用text封装sql去执行。）。
  **验证点**：能创建 collection，上传文件记录入库；所有表可 CRUD。

---

## **Stage 1｜PDF解析与Element入库**

**目标**：完成文档结构化解析（文本、图片、表格、公式）。
**任务**

* 对接 MinerU API：生成 `content_list`。
* 实现章节层次修复（section_name, level_nav）。
* 生成 `text_content / image_base64 / bbox_json / page_no` 并插入 elements 表。
* 对 header 节点自动生成 `section_summary`。
  **验证点**：抽查 10 个元素字段完整性；数据库中每篇文档均有对应 element 记录。

---

## **Stage 2｜向量化与检索**

**目标**：可按 query 检索出相关 Elements。
**任务**

* 调用多模态 embedding 模型（文本/图片分通道）。
* 将 embedding 存入 `elements.vec_embedding` 字段（OceanBase 向量列或 pyobvector）。
* 实现 `/search/elements` 接口，支持：

  ```json
  { "query": "describe the training process", "top_k": 5 }
  ```
* 返回结构分桶（header / text / table / equation / image）。
  **验证点**：人工抽查检索 Top-5 命中率 ≥ 60%。

---

## **Stage 3｜问答闭环（Answer + Evidence）**

**目标**：打通单轮问答闭环。
**任务**

* 实现 Query Rewriter（LLM 改写为检索 query）。
* 调用 `/search/elements` 检回结果，编号 `[Evidence#]`。
* 构造 prompt（text:list, images:list 对齐）。
* 调用 VLM 生成答案；在 Markdown 输出中插入 `[Evidence1] [Evidence2] ...`。
* 写入 `chats / turns / evidence2element`。
  **验证点**：前端能显示答案，并能从答案锚点跳转到对应元素 bbox。

---

## **Stage 4｜历史对话与记忆（轻量版）**

**目标**：多轮问答可恢复上下文。
**任务**

* 读取上一轮 `question + answer + evidence_summary` 组成简易 memory。
* turn 结构：`{id, chat_id, user_question, llm_answer_md, thought_log, created_at}`。
* 支持加载历史对话与 evidence 映射。
  **验证点**：多轮问答时上一轮信息可复用；历史记录可回放。

---

## **Stage 5｜评测与提示词调优（DsPy集成）**

**目标**：建立可量化优化循环。
**任务**

* 构建评测集（10 篇论文 × 10 问）。
* 统计指标：Top-K 命中率 / Evidence 对齐准确率 / 答案一致性。
* 用 DsPy 自动调优 Query Rewriter 与 Answer Prompt。
  **验证点**：能跑离线评测脚本，记录得分变化。

---

## **Stage 6｜前端与系统集成（ReAct UI）**

**目标**：实现最小可用 UI。
**任务**

* 双栏界面：左侧对话区，右侧 PDF 高亮。
* 前端事件流与 `[Evidence#]` 跳转。
* 基础路由：Collections / Ask / Chats。
  **验证点**：能从前端提问并查看高亮 evidence。

---

## **Stage 7｜增强与可靠性**

**目标**：系统具备可运维性。
**任务**

* 请求链路日志与错误追踪。
* 降级策略：embedding / VLM 故障时仅展示检索结果。
* 数据一致性检查（evidence2element 与 Markdown 对齐校验）。
  **验证点**：异常时系统可优雅降级；日志链路完整。

---

## **Stage 8｜拓展方向（v3多跳检索）**

**目标**：支持复杂问题分解与多次检索。
**任务**

* 子问题拆解 → 多轮检索 → 答案整合。
* 前端展示思考链（思考框可视化）。
  **验证点**：在复合问题上比 v2 答案更正确。

---

## 💡并行横切关注

| 主题             | 要点                                                                              |
| -------------- | ------------------------------------------------------------------------------- |
| **数据一致性**      | `(chat_id, evidence_no)` 唯一；`documents.collection_id` 外键；Element 与 Evidence 对齐。 |
| **统一Prompt协议** | text 与 image 输入一一对应；Evidence 映射提前注入。                                            |
| **简化优先**       | v0–v2 不引入复杂 Agent / Memory / MCP。                                               |
| **日志与可回滚**     | 所有生成前后均保存日志与版本号，方便追溯。                                                           |

