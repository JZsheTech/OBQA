# 一、项目概述

**Arxiv 论文检索与收藏系统**：基于 arXiv API 的 Web 端检索 + 本地收藏。前端 React（Vite），后端 FastAPI + SQLAlchemy（MySQL 为主，SQLite 兼容），统一通过 `backend/app/utils/arxiv_client.py` 访问 arXiv，避免频繁请求（`demo_test` 仅保留命令行示例包装）。

> ⚠️ 环境配置和服务启动都由开发者手动执行，仓库仅提供代码与静态说明。

---

## 目录结构

```
.
├─backend/              # FastAPI 服务
│  ├─app/               # 业务代码
│  └─requirements.txt   # 后端依赖
├─frontend/             # React + Vite 前端
├─demo_test/            # arxiv_client 及命令行 Demo
├─需求文档.md
├─设计文档.md
└─readme.md
```

---

## 后端（FastAPI）

### 环境变量

| 变量 | 说明 | 示例 |
| --- | --- | --- |
| `DATABASE_URL` | SQLAlchemy 连接串 | "mysql+pymysql://root:@127.0.0.1:2893/test?charset=utf8mb4" |
| `CORS_ALLOW_ORIGINS` | 允许的前端源，逗号分隔，可选 | `http://localhost:5373` |

> 默认 `DATABASE_URL=sqlite:///./arxiv.db` 便于本地快速跑通。

"mysql+pymysql://root:@127.0.0.1:2893/test?charset=utf8mb4"

### 安装与启动（手动执行）

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8179
```

* 端点示例：
  * `POST /api/arxiv/search`：按参数检索 arXiv，内部强制 `max_results<=50`，使用 `backend/app/utils/arxiv_client.py`，默认 `delay_seconds=3`、`num_retries=3`。
  * `POST /api/papers/save`：收藏一条论文到本地数据库（去重、可附带 tags/note）。
  * `GET /api/papers/saved`：收藏列表，支持关键词/作者/分类/标签过滤与分页。
  * `GET /api/papers/{id}`：收藏详情。
  * `PATCH /api/papers/{id}`：更新 tags/note。
  * `DELETE /api/papers/{id}`：取消收藏。

### 数据库

* 结构与设计文档一致，`backend/schema.sql` 可直接执行（MySQL）。
* SQLAlchemy 模型见 `backend/app/models.py`，`Base.metadata.create_all` 会在应用启动时创建表（若数据库用户有权限）。
* `authors` / `categories` 使用 JSON 字符串存储，后端序列化/反序列化。

### 模块拆分

* `backend/app/main.py`：入口、CORS、路由注册、健康检查。
* `backend/app/routers/search.py`：arXiv 检索。
* `backend/app/routers/papers.py`：收藏 CRUD。
* `backend/app/repositories.py`：数据库读写与模型转换。
* `backend/app/utils/arxiv_client.py`：统一 arXiv 访问层（50 条上限、3s 间隔、重试 3，供后端路由调用）；`demo_test` 目录仅保留命令行 Demo 的薄封装。

---

## 前端（React + Vite）

### 安装与启动（手动执行）

```bash
cd frontend
npm install          # 或 pnpm/yarn
# npm run dev          # 默认 5173 端口
npm run dev -- --host --port 5373
```

* Vite 代理将 `/api` 转发到 `http://localhost:8179`（见 `frontend/vite.config.ts`）。
* 主要页面：
  * `/search`：检索页。支持关键词/标题/摘要/作者/分类、时间范围、排序、数量。结果卡片可直接收藏（可附 tags/note）。
  * `/saved`：收藏列表，支持过滤、排序、分页，内联编辑 tags/note，删除。
  * `/papers/:id`：收藏详情，可编辑 tags/note，跳转 PDF/Arxiv。
* UI 风格：深色背景 + 渐变，高对比度操作按钮，响应式布局。

---

## 运行与检查建议

1) **后端依赖**：确保安装 `backend/requirements.txt`，并设置好 `DATABASE_URL` 可写入表。  
2) **创建表**：可直接执行 `backend/schema.sql` 或让 FastAPI 自动创建。  
3) **前端依赖**：安装 npm 依赖，确保端口与代理匹配后端。  
4) **静态检查**：可选 `python -m compileall backend`、`npm run build -- --mode development` 做静态编译检查。  
5) **运行**：先启动后端 `uvicorn app.main:app --reload --port 8179`，再 `npm run dev` 打开前端。  

> 如需在 CLI 快速体验，可使用 `demo_test/search_demo.py` 直接查询 arXiv。

---

## TODO / 可扩展

* 增加 Redis 缓存相同查询。
* 引入用户体系（saved_papers 增加 user_id）。
* 收藏列表高级过滤（作者拆表、JSON 索引）。
* 加入任务队列做批量刷新/订阅。
