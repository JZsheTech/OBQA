# EviQAsys / OBQA 多模态论文问答系统

本仓库实现了一个**可展示 Evidence 的多模态论文问答 Demo**，围绕「一组 PDF 论文 → 解析入库 → 向量检索 → 基于证据的问答」这一闭环进行工程化落地。  
后端以 FastAPI + OceanBase + MinerU + DSPy 为主干，前端以 React 为基础，结合 Figma 设计稿实现知识库与问答界面。

> 说明：本 README 主要帮助后续 AI coder / 开发者快速建立全局认知，详细行为规范请始终以 `docs/zh` 下的设计文档为准。

---

## 1. 文档地图（从这里开始）

系统的设计文档全部在 `docs/zh` 中，根目录下的同名 .md 只是快捷入口。

- 需求与架构
  - `docs/zh/多模态论文问答系统需求文档.md`：系统目标、功能范围、约束与简化条件。
  - `docs/zh/多模态论文问答系统设计文档.md`：**唯一权威架构文档**，定义了端到端流程、API 约定、Evidence 策略等。
- 数据与工程细节
  - `docs/zh/数据模型.md`：OceanBase 表结构与实体关系（collections / documents / elements / chats / turns / turn2element）。
  - `docs/zh/技术栈.md`：前后端、数据库、MinerU、vLLM / DSPy 等技术选型与嵌入配置。
  - `docs/zh/工程细节/dspy问答Agent设计.md`：M4 问答 Agent 的编排设计，与 `services/qa_flow` 目录对应。
  - `docs/zh/工程细节/Evidence渲染规范.md`：`[Elem#id]` 与 `[Evidence#no]` 的映射及前后端职责划分。
  - `docs/zh/开发路线图.md`：M0–M6 里程碑描述和 DoD。
- 前端交互与布局
  - `docs/zh/前端页面组织逻辑设计.md`：页面分解（知识库主页 / Collection 页 / Document 页 / Chat 页 / 历史页）和组件布局。
  - `dependency/frontUI_design/`：从 Figma 导出的前端 UI 设计项目（Vite+React 模板），用作实现参考。
- 分阶段开发日志
  - `docs/dev_log/M0`–`M4`：各阶段的实现笔记与修正说明，辅助理解历史决策。

如果需要为某个功能写代码，推荐阅读顺序：

1. `多模态论文问答系统需求文档.md`
2. `多模态论文问答系统设计文档.md`
3. `数据模型.md` + `技术栈.md`
4. 对应工程细节文档（DSPy / Evidence / 路线图）
5. 对应代码目录下的实现（见下一节）

---

## 2. 仓库结构总览

只列出与当前 Demo 直接相关的主干目录：

```text
.
├── EviQAsys
│   ├── backend              # FastAPI 后端
│   │   └── app
│   │       ├── api          # HTTP 路由与 Pydantic schema
│   │       ├── repositories # OceanBase 表网关（无 ORM）
│   │       ├── schemas      # API 层数据模型
│   │       └── services     # 业务服务：ingestion / retrieval / qa_flow / ...
│   └── frontend             # React + Vite 前端工程
│       └── src
│           ├── api          # 前端 fetch 封装
│           ├── components   # 基础 UI 组件
│           └── pages        # 页面级组件（当前仅有 Home + Documents 控制台）
├── docs
│   ├── zh                   # 中文设计文档（权威）
│   └── dev_log              # M0–M4 开发日志
├── dependency
│   ├── frontUI_design       # 前端 Figma UI 导出工程
│   ├── oceanBaseDemo        # OceanBase 连接 & DDL 示例
│   └── minerUparseDemo      # MinerU PDF 解析示例
├── sample_data              # 真实 PDF / 解析样例（外部挂载）
└── log                      # 运行日志目录（外部挂载）
```

> 注意：`sample_data/` 与 `log/` 为外部挂载目录，遵循 AGENTS.md 要求，不应在版本库中写入新数据。

---

## 3. 技术栈与外部服务

结合 `docs/zh/技术栈.md`：

- 前端：React + Vite（`EviQAsys/frontend`），以浏览器内运行的桌面 Web App 为主。
- 后端：Python + FastAPI（Conda 环境 `quest`），集中在 `EviQAsys/backend/app`。
- 数据库：OceanBase（Docker 单节点），通过 `repositories/sql/schema.sql` 初始化。
- 文档解析：MinerU，本地以 FastAPI 服务在独立 Conda 环境 `jzMinerUVllm` 中运行。
- 嵌入与检索：
  - vLLM 暴露 OpenAI `/v1/embeddings` 兼容接口（默认模型 `jinaembeddingv4`，`VECTOR_DIM=2048`）。
  - 嵌入服务：`services/embedding/embedding_service.py`。
  - 检索服务：`services/retrieval/retriever.py`，在 Python 侧做 TopK 相似度计算，支持向量/全文模式。
- LLM 编排与 Agent：
  - DSPy（`dspy`）用于文本任务编排（问句重写、答案生成、记忆摘要等），在 `services/llm` 与 `services/memory` 中落地。
  - 默认 LLM：文本链路使用 `x-ai/grok-4.1-fast`（OpenRouter）；`use_image=true` 且携带图片时 AnswerAgent 切换到视觉模型 `x-ai/grok-4-fast`，提示词按文本/多模态两套模板分流。

---

## 4. 后端架构与主要模块

### 4.1 FastAPI 应用与启动方式

- 入口：`EviQAsys/backend/app/main.py`
  - 创建 `FastAPI(title="EviQAsys API")` 实例。
  - 在 `startup` 事件中调用 `initialize_database()`，自动执行 `repositories/sql/schema.sql` 以创建/升级表结构。
  - 挂载 CORS 中间件（当前允许任意来源，便于前端本地开发）。
  - 注册 API 路由：`from .api import api_router`，统一前缀 `/api`。
  - 健康检查：`GET /healthz -> {"ok": true}`。

开发环境启动示例（结合 AGENTS.md）：

```bash
conda activate quest
cd EviQAsys/backend
uvicorn EviQAsys.backend.app.main:app --app-dir EviQAsys/backend --reload --port 9075
```

> 前端默认通过 `http://127.0.0.1:9075` 访问后端，其中 `/healthz` 用于 Home 页健康检查，`/api` 用于业务接口。

### 4.2 数据库 schema 与仓储层

- schema 文件：`EviQAsys/backend/app/repositories/sql/schema.sql`  
  根据 `docs/zh/数据模型.md` 定义并演进六张核心表：
  - `collections`：知识库集合（名称、描述、创建时间）。
  - `documents`：上传的 PDF 元数据与全文 markdown（`md_text`）、摘要 `abstract` 等。
  - `elements`：从 MinerU 解析出的最小检索单元（段落、标题、图像、表格、公式），包含：
    - 结构字段：`elem_type/header_name/header_level/level_nav/order/page_no` 等；
    - 文本字段：`raw_text_content`（原始）、`text_content`（带文档/页码/章节前缀及上下文的增强文本）、`text_caption`；
    - 嵌入、定位：`vec_embedding`（`VECTOR(VECTOR_DIM)`）、`bbox_json`、`image_base64`；
  - `chats`：会话（Collection 级或 Document 级），记录 `type/collection_id/document_id/max_turn_order` 等。
  - `turns`：单轮问答，存储 `user_question` 与 `llm_answer_text`（保留 `[Elem#<element_id>]` 锚点）。
  - `turn2element`：桥表，按 `(chat_id, turn_id, element_id)` 记录某轮回答实际引用到的元素。
- 仓储层目录：`EviQAsys/backend/app/repositories`
  - 按表拆分：`CollectionsRepository / DocumentsRepository / ElementsRepository / ChatsRepository / TurnsRepository / Turn2ElementRepository`。
  - 通过直接 SQL 与 OceanBase 交互，不引入 ORM，便于与 `schema.sql` 对齐。

在实现新数据访问逻辑时，应优先扩展对应的 Repository，而不是在 service 中直接写 SQL。

### 4.3 文档上传与 MinerU 解析（M2 主线）

相关模块：

- API 路由：`api/routes/collections.py`
  - `GET /api/collections`：返回所有 collections 列表。
  - `GET /api/collections/{collection_id}/documents`：返回当前 collection 下的文档列表（包含 `file_name/file_size_bytes/element_count/created_at/parse_status`）。
  - `POST /api/collections/{collection_id}/documents`：接收 PDF 文件上传，调用 ingest 流程。
- 服务层：
  - `services/ingestion/document_ingestor.py`：`DocumentIngestor.ingest_upload(collection_id, file)`
    - 校验 collection 是否存在；
    - 校验文件类型，只允许 `.pdf`；
    - 计算 SHA-256 与大小，做上传去重（抛出 `DuplicateDocumentError`）。
    - 将文件保存到 `UPLOAD_DIR`（由 `UploadSettings` 控制）。
    - 调用 MinerU 解析（`services/integrations/MinerUAdapter`），拿到 `content_list / images / md_text`。
    - 经 `services/parser`：
      - `header_processor.preprocess_headers`：修正标题层级，构造 `header_level/level_nav/order_start/order_end`，并生成章节摘要；同时将 MinerU 返回的页眉元素（`type="header"`）视作噪声，等同 `discarded` 直接丢弃，避免写入 elements/chunks。
      - `unifier.normalize_element`：统一构造 `elem_type/text_content/raw_text_content/page_no/bbox_json/text_caption/image_base64`。
    - 通过 `ElementsRepository.batch_insert` 写入 `elements` 表，更新 `documents.element_count` 等。

当前前端的 `DocumentsPage`（见 §6）基于以上 API 提供一个“上传 PDF + 查看解析状态”的控制台，用于快速验证 MinerU 流程。

### 4.4 嵌入与检索（M3 主线）

相关模块：

- 配置：`env_setting.py`
  - `VECTOR_DIM`：嵌入维度（默认 2048，对齐 `jinaembeddingv4`）。
  - `EmbeddingSettings`：`EMBEDDING_ENDPOINT / EMBEDDING_MODEL / EMBEDDING_TIMEOUT_S / EMBEDDING_MAX_RETRIES` 等。
- 嵌入服务：`services/embedding/embedding_service.py`
  - 封装对 vLLM OpenAI 兼容接口的调用。
  - 写入前校验返回向量维度与 `VECTOR_DIM` 一致。
- 检索服务：`services/retrieval/retriever.py`
  - `Retriever.retrieve_topk(collection_id, query_text, top_k, doc_id=None, elem_types=None, search_mode="vector"|"fulltext")`
  - 在 Python 侧聚合/过滤候选元素（按 collection / document / elem_type），并计算相似度得分，返回包含 `element_id/elem_type/text_content/doc_id/page_no/bbox/score` 等字段的列表。
- API 路由：`api/routes/retrieval.py`
  - `GET /api/retrieval/test`：调试用检索接口，返回 `RetrievalEnvelope(code="OK", data=[RetrievalCandidate, ...])`。

手工验证推荐走 `EviQAsys/backend/tests/manual` 下的脚本（遵循 AGENTS.md 的“仅手工执行测试脚本”要求），例如：

- `test_m2_ingest.py`：验证 MinerU 解析与元素落表。
- `test_m3_e2e_documents_parse_and_query.py`：完成上传→解析→嵌入→检索的端到端流程。

### 4.5 问答流程与 Evidence 策略（M4 主线）

相关文档与模块：

- 文档：`docs/zh/工程细节/dspy问答Agent设计.md`、`docs/zh/工程细节/Evidence渲染规范.md`。
- 核心 orchestrator：`services/qa_flow/qa_orchestrator.py`
  - 输入：`chat_id`、用户 `question`、检索 TopK、是否开启 `use_image`、记忆相关参数。
  - 步骤概览：
    1. 解析 chat 范围（collection/document），读取历史 turn 的 memory。
    2. TextRetrieveAgent 做文本检索（可选页过滤）；use_image=true 时 ImageRetrieveAgent 做图片检索。
    3. MemoryAgent 从历史记忆中挑选相关元素（文本/图片分支可独立关闭）。
    4. 按 element_id 去重合并候选元素，保持检索顺序优先。
    5. AnswerAgent 直接用 text+image 元素生成回答（图片通过 OpenAI 多模态接口传入），回答中引用 `[Elem#<id>]`。
    6. turns 表写入回答与 memory，更新 chats.max_turn_order，构建 evidence_no 映射并返回。
- API 路由：`api/routes/chats.py`
  - `POST /api/chats/{chat_id}/turns`
    - 请求体：`TurnCreateRequest`（`question`, 可选 `use_image/text_retrieve_topk/image_retrieve_topk/text_memory_topk/image_memory_topk/use_page_in_text_retrieve/page_retrieve_topk/text_search_mode`）。
    - 返回：`TurnResponseEnvelope(code="OK", data=TurnResponse)`，其中：
      - `answer_text`：包含 `[Elem#<element_id>]` 锚点的 LLM 文本；
      - `evidences`: `EvidenceItem` 数组（`element_id/evidence_no/document_id/page_index/bbox/elem_type/snippet/title`）。

> 重要约定：数据库与后端内部统一在回答文本中使用 `[Elem#id]`；`evidence_no` 仅作为前端展示编号，不入库，并由后端在返回 API 前基于 chat 历史动态生成。

---

## 5. 当前后端 API 速览

当前代码中已落地的主要接口（均挂载在 `api_router` 下，统一前缀 `/api`，`/healthz` 除外）：

- 健康检查
  - `GET /healthz` → `{"ok": true}`
- Collection 与文档
  - `GET /api/collections`
    - 响应：`{"code":"OK","data":[{id,name,description,created_at}, ...]}`。
  - `GET /api/collections/{collection_id}/documents`
    - 响应：`{"code":"OK","data":[{id,collection_id,file_name,file_size_bytes,element_count,created_at,parse_status}, ...]}`。
  - `POST /api/collections/{collection_id}/documents`（multipart/form-data，字段 `file`）
    - 成功：`{"code":"OK","data":{doc_id,file_name,file_size_bytes,status}}`。
    - 失败：
      - 非 PDF 上传：400 + `{"detail": "Only PDF uploads are supported."}`。
      - 重复上传：409 + `{"detail": "... DuplicateDocumentError ..."}`。
- 检索调试
  - `GET /api/retrieval/test`
    - Query 参数：`collection_id`、`query`、`top_k`、可选 `doc_id/elem_types/search_mode`。
    - 响应：`{"code":"OK","data":[{element_id,elem_type,doc_id,page_no,bbox,score,text_content,...}, ...]}`。
- 问答主流程
  - `POST /api/chats/{chat_id}/turns`
    - 请求体：`{"question": "...", "top_k": 8, "enable_image_vqa": false, "enable_memory_summarizer": false}`。
    - 响应示例（简化）：
      ```jsonc
      {
        "code": "OK",
        "data": {
          "turn_id": 1,
          "chat_id": 3,
          "answer_text": "… as shown in [Elem#123] and [Elem#45].",
          "evidences": [
            {
              "element_id": 123,
              "evidence_no": 1,
              "document_id": 5,
              "page_index": 9,
              "bbox": [100, 120, 250, 300],
              "elem_type": "image",
              "snippet": "Figure 3. Overall architecture …",
              "title": "[doc=Paper Title] [page=10] [nav=…]"
            }
          ]
        }
      }
      ```

> Chat 创建、Chat 列表、按 Collection / Document 维度的 Chat 关联 API 尚未完全实现，但相关 schema（`schemas/chat.py`）和数据表（`chats`）已经就绪，可按 `docs/zh/多模态论文问答系统设计文档.md` 中的接口规划继续补齐。

---

## 6. 前端架构与 UI 设计

### 6.1 前端工程现状

目录：`EviQAsys/frontend`

- 工程模板：
  - 标准 Vite + React 模板（参考 `EviQAsys/frontend/README.md`），入口在 `src/main.jsx`。
  - 路由：`src/App.jsx` 使用 `react-router-dom` 注册：
    - `/` → `pages/Home.jsx`：展示后端 `GET /healthz` 状态，并提供跳转入口。
    - `/documents` → `pages/DocumentsPage.jsx`：简易文档上传 & 列表控制台。
- API 封装：`src/api/client.js`
  - `VITE_API_BASE`（默认 `http://127.0.0.1:9075/api`）。
  - `healthCheck()`：调用 `/healthz`。
  - `listDocuments(collectionId)`：调用 `GET /api/collections/{collection_id}/documents`。
  - `uploadDocument(collectionId, file)`：调用 `POST /api/collections/{collection_id}/documents`。
- 基础组件：
  - `components/UploadForm.jsx`：选择 PDF 并触发上传。
  - `components/DocumentList.jsx`：表格展示文档名称、大小、创建时间、元素数量及解析状态。

当前前端实现主要服务于 M2/M3 流程调试（上传 + 解析状态查看），完整的知识库导航和问答界面将在 M5 阶段按设计文档逐步落地。

### 6.2 UI/交互设计蓝图（M5 目标）

详见 `docs/zh/前端页面组织逻辑设计.md` 和 `dependency/frontUI_design`。

关键页面（均有详细布局说明）：

- 页面 1：**知识库主页（Collections Home）**
  - 展示所有 `Collection` 的列表（名称 / 创建时间 / 描述摘要）。
  - 支持按 name / description 搜索与筛选，新建 Collection 的弹窗。
- 页面 2：**Collection 管理页**
  - 左侧：当前 Collection 的文档列表、上传文档按钮、文档搜索（按 title / abstract / md_text）。
  - 右侧：Collection 层级的 Chat 历史与简易 RAG 检索（直接展示命中的 `text_content`）。
- 页面 3：**Document 管理页**
  - 展示文档元信息（所属 Collection / title / file_name / num_pages / element_count）与 Abstract 文本。
  - 提供 Document 级 RAG 搜索与 Document chat 历史列表。
- 页面 4：**Collection Chat with Evidence**
  - 三栏布局：左侧 Chat（问答列表 + 输入框）、中间 PDF Viewer（多文档切换）、右侧 Collection Chat 历史侧边栏。
  - 回答中每个 `[Evidence#no]` 可点击，驱动 PDF Viewer 按 `doc_id/page_no/bbox` 跳转并高亮对应 element。
- 页面 5：**Document Chat with Evidence**
  - 双栏布局 + 侧边栏：左侧 Chat，右侧固定单文档 PDF Viewer，侧边栏展示 Document chat 历史。
- 页面 6：**Chat 历史页**
  - 分别展示 Collection / Document 级的 chat 列表，可按创建时间排序，点击跳转到对应 Chat 页。

前端需要严格遵循《Evidence 渲染规范》：

- React 列表 key 使用 `element_id`，不用 `evidence_no`。
- 前端只渲染 `[Evidence#no]`，不自行生成 evidenceNo；`element_id → evidence_no` 映射来自后端返回的 `evidences`。
- 渲染时解析 `answer_text` 中的 `[Elem#id]`，用对应的 Evidence tag 组件替换并绑定点击事件，实现 PDF 高亮联动。

---

## 7. 环境配置与运行流程建议

### 7.1 前提条件

- Conda 环境：
  - `quest`：FastAPI / DSPy / OceanBase client 等。
  - `jzMinerUVllm`：MinerU PDF 解析服务。
- 数据库：本地或服务器上的 OceanBase Docker 实例（配置见 `env_setting.py` 中的 `OceanBaseSettings`）。
- Node.js：用于前端开发（推荐 LTS）。
- 本地或远程 vLLM / LLM 服务：用于 embeddings 和回答生成（通过 OpenAI 兼容 API 暴露）。

### 7.2 推荐的端到端开发步骤（单机）

1. **启动 OceanBase**
   - 参考 `dependency/oceanBaseDemo` 中的脚本和说明，启动单节点 OceanBase，并确认连接参数与 `env_setting.py` 中默认值一致或设置相应环境变量（`OB_HOST/OB_PORT/OB_USER/OB_PASSWORD/OB_DEFAULT_DATABASE`）。
2. **启动 MinerU 服务**
   - `conda activate jzMinerUVllm`
   - 参考 `dependency/minerUparseDemo/parse_pdf_minerU.py` 启动 MinerU HTTP 服务（确保 `MINERU_ENDPOINT` 对应地址可用）。
3. **启动嵌入与 LLM 服务**
   - 部署本地 vLLM 并暴露 `/v1/embeddings`，配置 `EMBEDDING_ENDPOINT/EMBEDDING_MODEL`。
   - 配置 LLM 接口：`LLM_API_BASE/LLM_MODEL_NAME/LLM_API_KEY` 等（见 `LLMSettings`）。
4. **启动后端**
   - `conda activate quest`
   - `cd EviQAsys/backend`
   - `uvicorn EviQAsys.backend.app.main:app --app-dir EviQAsys/backend --reload --port 9075`
   - 首次启动会自动运行 `schema.sql` 创建/升级表结构。
5. **准备最小数据**
   - 当前版本尚未提供 `POST /api/collections` API，可通过以下方式创建 Collection：
     - 直接在 OceanBase 中执行 `INSERT INTO collections (name, description) VALUES (...);`；
     - 或编写临时 Python 脚本调用 `CollectionsRepository.create(...)`（不建议长期保留）。
   - 记下 `collection_id`，用于前端上传文档。
6. **前端控制台验证 MinerU 流程**
   - `cd EviQAsys/frontend`
   - `npm install`（首次）后执行 `npm run dev`。
   - 在浏览器访问前端（默认 `http://localhost:5173`），在 Home 页确认 Backend Health 为 OK。
   - 进入 `/documents` 页面，输入 `collection_id`，上传 PDF，并观察解析状态（`uploaded` → `parsed`）。
7. **手工验证检索与问答**
   - 使用 `GET /api/retrieval/test` 或 `tests/manual` 下脚本验证嵌入与检索：
     - 例如 `python EviQAsys/backend/tests/manual/test_m3_e2e_documents_parse_and_query.py`。
   - 在准备好 Chat 数据后，通过 `POST /api/chats/{chat_id}/turns` 验证 M4 问答流程（可使用 `test_m4_qa_flow.py` / `test_m4_multi_turn_qa_flow.py` 等脚本）。

> 测试脚本均设计为**手工执行**、依赖真实解析结果和数据库记录；不要在 CI 中自动运行，也不要使用 mock 数据。

---

## 8. 里程碑进度与后续工作

结合 `docs/zh/开发路线图.md` 与 `docs/dev_log`，当前项目大致处于：

- ✅ M0：开发环境与空 API
  - FastAPI 框架、`GET /healthz` 已完成。
- ✅ M1：数据库初始化与仓储层
  - OceanBase schema 与六张表已落地，Repository 层已可用。
  - `/api/collections` 初版读接口已实现。
- ✅ M2：文档上传 → MinerU 解析 → 入库
  - `POST /api/collections/{id}/documents` 已实现上传 + 解析 + 元素入库。
  - 前端提供 Document 控制台用于验证解析结果。
- ✅ M3：向量化与检索
  - 嵌入服务与检索服务已实现，`/api/retrieval/test` 可返回候选元素。
- ✅ M4：问答主干与 Evidence 策略
  - `services/qa_flow` 的 orchestrator 与 Evidence 映射逻辑已实现。
  - `POST /api/chats/{chat_id}/turns` API 已提供端到端问答能力。
- 🚧 M5：前端页面与 Evidence 高亮
  - 当前只完成了最小健康检查页 + 文档控制台。
  - 完整的 Collection / Document / Chat / PDF Viewer / Evidence 高亮页面仍按设计文档逐步实现。

未来工作重点（面向 AI coder / 开发者）：

- 按 `开发路线图` 中 M5a–M5d 的拆解，实现前端路由骨架、API 对齐、文本形态 QA 展示，再到 Evidence 高亮与 PDF 联动。
- 在后端补齐 Chat 创建与列表 API，使前端可通过 API 完成 Collection / Document / Chat 全链路创建。
- 随着实现推进，及时更新 `docs/zh` 中对应章节，使其与代码保持一致。

---

## 9. 面向 AI coder 的快速上手建议

当你以“AI coder”的身份接手某个改动/新功能时，可以按如下路径理解上下文：

1. **先读文档，再看代码**
   - 需求 & 设计：`docs/zh/多模态论文问答系统需求文档.md` + `多模态论文问答系统设计文档.md`。
   - 若涉及数据结构：同步查阅 `docs/zh/数据模型.md`，确保字段命名 / 约束不被破坏。
   - 若涉及 Evidence 或问答流程：查阅 `docs/zh/工程细节/dspy问答Agent设计.md` 与 `Evidence渲染规范.md`。
2. **用目录定位模块**
   - API 变更：从 `EviQAsys/backend/app/api/routes` 入手，同时查阅对应 `schemas` 与 `services`。
   - 数据访问：尽量通过 `repositories` 扩展，而非直接拼 SQL。
   - 解析 / 向量化：集中在 `services/parser`、`services/ingestion`、`services/embedding`、`services/retrieval`。
   - 问答编排：`services/qa_flow` + `services/llm` + `services/memory` + `services/mapping`。
3. **保持前后端契约一致**
   - 遵守统一响应 envelope：成功 `{"code":"OK","data":...}`，错误 `{"code":"SOME_ERROR","message":"..."}`（老接口如果仍返回 `detail`，在改动时可以顺手统一）。
   - 不在回答文本中引入 `[Evidence#no]`，只使用 `[Elem#id]`；Evidence 编号由后端统一计算。
4. **遵循 AGENTS.md 中的约束**
   - 不新增 pytest / CI 自动测试；如需验证，请按现有模式添加独立的 `tests/manual/*.py`。
   - 不使用 mock 数据；测试脚本只能依赖真实解析结果与真实数据库。
   - 不写入 `sample_data/` 与 `log/`。
5. **每次改动同步更新文档**
   - 如行为与 `docs/zh` 中描述发生偏差，应优先更新文档，再对代码进行调整或在文档中注明差异原因。

通过以上路径，可以在不迷失细节的前提下快速定位到正确的模块，并保持与现有设计文档的一致性。
