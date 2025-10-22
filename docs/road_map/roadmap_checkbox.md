非常好 👍 ——下面是一个**可直接复制到 GitHub / Cursor / Notion 的「可勾选 issue 清单模板」**，按照你刚才那份 RoadMap 分为四大维度：**前端 / 后端 / 数据层 / 评测与调优**。
它遵循最小可行 → 可验证 → 可维护的演进路线（v0 → v3）。

---

# 🧭 PaperEvidenceQA 开发总览 Checklist

> 技术栈：ReAct（前端） + FastAPI（后端） + OceanBase（数据库） + DsPy（Prompt 优化）
> 数据模型：collections / documents / elements / chats / turns / evidence2element

---

## 🧱 Phase 0：基础骨架搭建（最小可运行）

**目标：能跑通 Collection + 上传文档 + 简单问答页面骨架**

### 🖥️ 前端 ReAct

* [ ] 初始化项目结构（Router / Layout / Sidebar / ChatPanel / PdfViewer）
* [ ] 配置全局状态管理（useContext 或 Zustand）
* [ ] 新建「Ask 页面」：左栏对话框 + 右栏 PDF 预览框
* [ ] 为 `[Evidence#]` 高亮跳转预留事件通道（先用 mock 数据）
* [ ] 添加通用组件（Loading / Toast / Modal）

### ⚙️ 后端 FastAPI

* [ ] 初始化 FastAPI 项目 + 结构化路由（/collections /documents /chats /turns）
* [ ] 实现基础 CRUD：创建 Collection / 上传 Document（文件路径记录）
* [ ] 接入 OceanBase，配置连接池与 Alembic 迁移脚本
* [ ] 定义 SQLAlchemy 模型（对应数据模型）
* [ ] 基础健康检查接口 `/health`

### 🗃️ 数据库 OceanBase

* [ ] 建立基础表结构（collections / documents / elements / chats / turns）
* [ ] 建立桥表（evidence2element，约束 `(chat_id, evidence_no)` 唯一）
* [ ] 编写初始化/回滚脚本（SQL + Alembic）

✅ **退出标准**：能创建 Collection / 上传 PDF 占位记录 / 打开 Ask 页面。

---

## 📄 Phase 1：文档解析与 Element 入库

**目标：能从 PDF 生成 Element 表记录，包含 bbox、section、page 等元信息**

### ⚙️ 后端

* [ ] 接入 MinerU API（或本地 docker 服务）
* [ ] 解析 JSON 输出 → 生成 Element 对象
* [ ] 规范化 section_name / level_nav / bbox_json / page_no
* [ ] 将 image 元素转换为 base64 并存储
* [ ] 插入数据库（`elements` 表）

### 🧪 验证

* [ ] 解析 3 篇论文，抽查 Element 表内容正确性（文本/图像/标题）
* [ ] 确保每个 Element 有 doc_id 外键
* [ ] 输出人工核对报告（命中 10 例可视化 bbox 预览）

✅ **退出标准**：任意 PDF 可解析为 Element 集合，结构与层级正确。

---

## 🔍 Phase 2：向量化与检索

**目标：能根据 query 检索出 top-K Elements**

### ⚙️ 后端

* [ ] 为 elements 表新增 vec_embedding 列
* [ ] 建立文本与图像两种 embedding 管道（统一存向量）
* [ ] 实现 `/search/elements` 接口：输入 query → 返回 top-K Elements
* [ ] 编写索引刷新脚本（批量生成 embedding）

### 🧪 验证

* [ ] 用 3 个 query 测试召回的 Element 是否相关
* [ ] 统计 top-5 命中率（人工检查）

✅ **退出标准**：给定问题能检回正确 Element，召回稳定。

---

## 💬 Phase 3：最小问答闭环

**目标：能实现「提问 → 检索 → 答案 + [Evidence#] → 高亮」的闭环**

### ⚙️ 后端

* [ ] 定义 `/qa/ask` 接口：输入 question，内部执行检索 → LLM 生成
* [ ] LLM 输出中嵌入 `[Evidence#]` markdown 锚点
* [ ] 生成 evidence2element 记录（chat_id, evidence_no, element_id）
* [ ] 校验 `[Evidence#]` 对应 element_id 是否存在

### 🖥️ 前端

* [ ] 在 ChatPanel 渲染带 `[Evidence#]` 的 Markdown
* [ ] 点击锚点时，高亮对应 PDF 区域（基于 bbox_json）
* [ ] 支持单文档单轮问答展示

✅ **退出标准**：v0.0 完成——单文档问答闭环可演示。

---

## 🧠 Phase 4：多轮对话与轻量记忆

**目标：能连续多轮对话，记住上文上下文（答案与证据）**

### ⚙️ 后端

* [ ] 实现 `/chat/{chat_id}/turns` 查询接口
* [ ] turn 表保存 llm_answer_md + thought_log
* [ ] Memory 机制：拼接最近 N 轮 Q/A + 关键 evidence 段落
* [ ] 多轮 prompt 拼接逻辑（长度控制）

### 🖥️ 前端

* [ ] 在左栏显示历史轮次
* [ ] 点击某轮可回看答案与证据
* [ ] 支持对话滚动加载与自动保存

✅ **退出标准**：多轮单文档问答正常，上下文可回溯。

---

## 🧩 Phase 5：多文档与 Collection 模式

**目标：可同时针对多个文档提问与检索**

### ⚙️ 后端

* [ ] `/qa/ask_collection` 接口：输入 question + collection_id → 跨文档检索
* [ ] 整合多篇论文的元素结果，去重后统一生成答案
* [ ] 跨文档 evidence2element 绑定（不同 doc_id）

### 🖥️ 前端

* [ ] 右侧 PDF Viewer 可切换多篇文档
* [ ] 每篇文档高亮独立维持
* [ ] Collection 页面：展示所有文档摘要与状态

✅ **退出标准**：v1.0——多文档问答可展示与高亮。

---

## ⚗️ Phase 6：评测与提示词优化（DsPy）

**目标：建立可重复评测机制 + 自动提示词搜索**

### 📊 评测集

* [ ] 选 10–20 篇论文，人工标注 Q / 标准 Evidence
* [ ] 存储为 QA 测试集 JSON

### ⚙️ 调优

* [ ] 构建 DsPy pipeline：

  * 模块 1：Query Rewriter
  * 模块 2：Answer Generator
* [ ] 自动搜索最佳 Prompt / 模板组合
* [ ] 对比不同 Prompt 的正确率、Evidence 命中率

✅ **退出标准**：DsPy 评测回路可自动跑完一次，输出指标。

---

## 🧰 Phase 7：运维与可靠性

**目标：系统可回滚、可观测、可降级**

### ⚙️ 后端

* [ ] 统一日志链路（question → hits → evidence_map → answer）
* [ ] 异常分类与重试机制
* [ ] 限流与熔断策略（模型超时自动降级展示检索结果）
* [ ] 数据一致性检查：evidence2element ↔ Markdown 对齐

### 🧪 验证

* [ ] 模拟模型超时、向量检索异常 → 能优雅降级
* [ ] 日志中能完整追溯一次 QA 流程

✅ **退出标准**：系统具备演示级鲁棒性。

---

## 🔬 Phase 8：复杂多跳问答（v3）

**目标：引入“复杂问题分解 + 多次检索”的高级 Agent 流程**

* [ ] DsPy 定义多轮子问题生成模块（A1→A2→A3）
* [ ] 每步子问题结果补全到下轮检索
* [ ] 思考框可视化中间推理路径
* [ ] 评测集扩展为多跳问题

✅ **退出标准**：多跳复合问题正确率提升 ≥ v2。

---

## 📘 持续任务（跨阶段）

* [ ] 🧩 Schema 文档维护（数据库字段 + 前后端接口）
* [ ] 🧪 单元测试 / 集成测试脚本完善
* [ ] 🧠 日志 + Prompt + Evidence 映射可视化
* [ ] 🚀 部署脚本与镜像（Docker Compose + 环境变量）
* [ ] 📦 README + 项目文档撰写

---

是否希望我把上面这份 checklist 转换成一个 **GitHub Project Issue 模板 (markdown + 标签)** 或者一个 **Cursor “任务看板结构 JSON” 文件**？
我可以帮你自动生成适配格式，便于你一键导入。
