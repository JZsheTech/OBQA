# 技术栈：

前端： ReAct
后端: FastAPI
数据库： OceanBase (我会在推进过程中逐步补充相关的数据库操作demo)
Agent组织和提示词调优： DsPY

# 数据模型

## 基础表
collections(id, name, created_at)
documents(id, collection_id, file_name, file_path, num_pages, meta_json)
elements(id, doc_id, elem_type, section_name, level_nav, text_content, text_caption, image_base64, bbox_json, page_no, vec_embedding)

chats(id, collection_id, created_at)
turns(id, chat_id, user_question, llm_answer_md, thought_log, created_at)


## 桥表(多对多)

每个chat中evidence_no都从1开始编号，并且唯一关联到一个element_id
evidence2element(chat_id, evidence_no, element_id)

请你再根据这些信息，给出一个具有宏观概括性质的RoadMap，来指导我一步步地完成系统的搭建。RoadMap不用涉及到很具体的细节，我会在每个阶段自己细化补充。
太好了，有了你的技术栈与数据模型，我们可以把“最小可用 → 渐进增强 → 可验证可运维”的路线一次性铺平。下面是一个**宏观 RoadMap**（阶段划分 + 里程碑 + 退出标准 + 风险与验证点），避免陷入早期细节泥潭，同时确保每一步都能被验证与回滚。

---

# v0 → v3 分阶段路线

## Phase 0｜基础设施与骨架（ReAct + FastAPI + OceanBase）

**目标**：把“跑起来”的最小骨架搭好，能创建 Collection / 上传文档 / 简单问答 UI 框架就绪。
**工作包**

* 前端（ReAct）初始化：路由（Collections / Ask / Ask All / Chats），左右双栏布局骨架（左对话、右 PDF 视图）与“下拉思考框”占位；引用编号从 1 开始的 UI 元素预留。参考需求文档的前端交互与双栏布局。 
* 后端（FastAPI）骨架：/collections /documents /chats /turns 的 RESTful；OceanBase 连接封装与基础测试脚本。
* 数据表落地：你给出的基础表与桥表先建起来（严格外键与唯一性约束：`(chat_id, evidence_no)` 唯一；`documents.collection_id` 外键）。
  **退出标准（Definition of Done）**
* 能创建 Collection、上传 PDF 占位记录、打开一个 Ask 页面（尚可用假数据渲染）。
* OceanBase 表结构与测试脚本稳定，CI 能一键初始化/回滚。 (我们没有已有数据需要迁移，都是从0开始工作)
  **关键风险与验证**
* UI 与“证据锚点”跳转的事件流要自始预留（即使 v0 先用假数据），避免后期返工。前后端设计已明确锚点与高亮的基本约定。

---

## Phase 1｜文档解析与元素级索引（MinerU → Elements）

**目标**：将 PDF 解析为 Element 粒度，补全层次字段，落表 `documents` 与 `elements`。
**工作包**

* 接入 MinerU，解析 `content_list` 与图片；生成 `section_name / level_nav`；为 header 聚合摘要；文档入库并绑定 Collection。 
* 统一检索文本：按类型组装 `text_content`；`image_base64`（图像类）入库；`bbox_json / page_no` 完备。
  **退出标准**
* 任意 PDF 可生成 Element 级记录，带 `section_name / level_nav / bbox / page_no`。
* 采样文档的**可视化抽查报告**（10 例）：确认标题层次修复正确、表图 caption 进 `text_content` 正确。
  **关键风险与验证**
* 章节层级修复的启发式是否稳定；若不稳，留回退策略（禁用层级修复但继续入库）。

---

## Phase 2｜向量化与检索（Embedding + OceanBase 存储）

**目标**：完成文本与图像的统一向量化，能够按 query 检回 top-K Elements。
**工作包**

* 向量字段：`elements.vec_embedding`；分文本/图片两路嵌入（表/公式以文本嵌入为主）。
* 基础检索 API：`/search/elements` 输入 query，返回按类型分桶（header / pure_text / table / equation / image）的 top-K。
  **退出标准**
* 给定问题可稳定检回与之相关的 5–10 个 Element；人工抽查 Top-5 命中率（粗评）。
  **关键风险与验证**
* 检索召回是否受 `text_content` 组装质量影响；需要**噪声鲁棒性测试**（问题扰动 / 同义改写）。

---

## Phase 3｜最小问答闭环（DsPy Prompt + Evidence 锚点）

**目标**：打通“提问 → 改写为检索 query → 答案 + [Evidence#] 锚点 → Evidence2Element 映射入库”的闭环。
**工作包**

* **Query Rewriter**：LLM 将用户问题改写为更检索友好的 query。
* **Answer Agent（VLM）**：根据检回的不同元素（文本/图片）组装 prompt（`text: List[str]` 与 `images: List[base64]` 一一对应），**同时**在答案内产出 `[Evidence#]`。
* 桥表写入：`evidence2element(chat_id, evidence_no, element_id)`（同一 chat 内 evidence_no 从 1 顺编并唯一）。
  **退出标准**
* **v0.0**：单文档单轮问答，答案中 `[1] [2] ...` 可点击，右侧 PDF 高亮跳转到对应 bbox。
  **关键风险与验证**
* `[Evidence#]` 和 `element_id` 的对齐：以**服务端渲染前校验**（缺失/越界即拒绝返回）保证一致性。设计里已经将锚点与 Element 一一映射并用于前端高亮。

---

## Phase 4｜前端体验与历史对话（Chats & Turns）

**目标**：把“像样的体验”做起来：对话历史、恢复上下文、思考框。
**工作包**

* 左右双栏 UI + 顶部论文切换（Ask Collection 时）：多文档问答时可在右栏切换 PDF。
* 保存 `chats / turns`，持久化 `llm_answer_md / thought_log`；加载历史对话可还原证据跳转。
  **退出标准**
* **v0.1**：单文档单轮问答历史可恢复；**v1.0**：单轮多文档问答可切换 PDF 并高亮跳转；**v1.1**：多文档历史可恢复。

---

## Phase 5｜多轮对话与轻量记忆（v2）

**目标**：多轮单/多文档问答；上一轮的答案与证据拼接为轻量 memory 供下一轮使用（长度受限）。
**工作包**

* Memory 策略：仅拼接若干轮的 `question + answer + [E#]→Element 摘要`，超长截断；不引入复杂 Memory。
  **退出标准**
* **v2.0**：多轮单文档；**v2.1 / v2.2**：多轮多文档与历史保存。 
  **关键风险与验证**
* 轮与轮间“指代歧义”导致检索漂移：在 DsPy 里加入**回指消解/实体补全**子模块作为可选 Rewriter。

---

## Phase 6｜质量评测与提示词调优（DsPy）

**目标**：建立可复现的评测与优化回路，而不是凭感觉调。
**工作包**

* 评测集：选 10–20 篇论文、每篇 5–10 个问题；标注理想 Evidence 元素或页码范围。
* 指标：答案一致性（人工 + 简单自动分），Evidence 对齐准确率（点击能否命中正确 bbox）、检索 Top-K 命中率。
* DsPy：为 Query 重写与 Answer 生成设定**候选模板/指令**，做离线格点搜索与小规模在线 A/B。
  **退出标准**
* 发布一版**评测看板**（命中率、对齐率、平均响应时延）。

---

## Phase 7｜可靠性与可运维（可回滚/可观测/可限流）

**目标**：把工程可靠性补齐，满足教学演示与迭代开发。
**工作包**

* 可观测：请求链路日志（question → rewritten query → hits → evidence map → answer）；错误分类与重试。
* 限流与熔断：VLM/Embedding 外部依赖故障时的降级（只展示检索结果，不生成答案）。
* 数据一致性：`evidence2element` 与答案 Markdown 在返回前做**一致性校验**，失败则回滚本轮 turn。
  **退出标准**
* 故障演练：杀掉向量服务 / VLM 服务能优雅降级；日志可追溯每个 `evidence_no` 对应的 `element_id`。

---

## Phase 8｜高级能力（v3 方向：多跳/多次检索的迭代式工作流）

**目标**：在有了稳定 v2 基础上，引入“复杂问题拆解为多轮 1 跳 + 多次检索”的智能化流程。
**工作包**

* 子问题分解与依赖串联：A1 结果补全到 A2 题干再检索的策略与 UI 呈现（思考框可视化中间结论）。
* 逐子问题“检索→回答→证据”循环，最后合并。这一模式在需求文档的 v3 路线已有明确表达。
  **退出标准**
* 在评测集的“复合问题”上优于 v2 的端到端正确率。

---

# 横切关注点（贯穿所有阶段）

* **证据对齐为“一等公民”**：锚点从 1 开始、与 Element 唯一映射、可点击高亮，这已在设计/需求里明确规定，是前后端对齐的契约。 
* **统一输入格式**：文本与图片双模输入的 prompt 组装规则固定，避免后期模型/接口切换导致大量重构。
* **简化优先**：v0–v2 明确不做复杂 Agent/MCP/重型 Memory，先把“能用且可验证”的主线跑通。

---

# 建议的阶段性里程碑（可作为每周目标）

1. **M0（第 1 周）**：骨架跑通（Phase 0）

   * ReAct + FastAPI + OceanBase 初始版，能创建 Collection/上传占位文档，Ask 页面骨架。

2. **M1（第 2 周）**：文档→元素入库（Phase 1）

   * 解析 3 篇论文完整入库；抽样可视化核验通过。

3. **M2（第 3 周）**：向量检索闭环（Phase 2）

   * `/search/elements` 稳定返回；Top-K 人工命中率有基线。

4. **M3（第 4 周）**：最小问答闭环（Phase 3）

   * v0.0 达成：单文档单轮问答 + 点击证据高亮跳转。

5. **M4（第 5–6 周）**：历史与多文档（Phase 4）

   * v0.1 / v1.0 / v1.1 依序落地：历史恢复、多文档切换。

6. **M5（第 7–8 周）**：多轮与轻量记忆（Phase 5）

   * v2.* 系列跑通；引入轻量 memory。

7. **M6（第 9 周+）**：评测与调优（Phase 6）

   * 看板上线；DsPy 迭代提示词与模板。

8. **M7（并行/持续）**：可靠性与运维（Phase 7）

   * 降级策略、日志链路、回滚机制稳定。

9. **M8（可选）**：多跳/多次检索（Phase 8）

   * 复合问题评测优于 v2。

---

如果你愿意，我可以把上面的 RoadMap 拆成一个**可勾选的 issue 清单模板**（分前端/后端/数据/评测四栏），便于你在 Cursor/GitHub 上逐条推进与追踪。
