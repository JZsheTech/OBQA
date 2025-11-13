M3 文档修复：

# 文档统一-只保留中文文档
- 由于同时维护docs/中zh版本的文档和en版本的文档会带来额外开销和不一致问题，我们决定后续只维护zh中文版本的文档，en版本的文档后续可以由用户手动删除。

- 中文文档中缺失的内容参考英文文档来补齐，比如docs/en/Architecture_Blueprint.md，这部分内容请直接补充到设计文档(docs/zh/多模态论文问答系统设计文档.md)中，不用单独开一个文档

- docs/zh/前后端交互逻辑设计.md 也请合并到 (docs/zh/多模态论文问答系统设计文档.md) 中。

- 合并后的设计文档 (docs/zh/多模态论文问答系统设计文档.md)需要统一组织和整理一下结构，不是简单的复制粘贴，而是整体重构，请你自主按照极简原型系统设计的规范来写。

# 1 API 基路径对齐

- 结论（以实现为准）：统一使用 API 基路径 `/api`。

- 代码依据：
  - 后端路由总前缀：`EviQAsys/backend/app/api/__init__.py:1` 中 `api_router = APIRouter(prefix="/api")`。
  - 实际路由示例：`EviQAsys/backend/app/api/routes/collections.py:1` 定义 `@router.get("/collections")`，对外完整路径为 `/api/collections`；文档上传为 `/api/collections/{collection_id}/documents`。
  - 健康检查：`EviQAsys/backend/app/main.py:1` 暴露 `/healthz`（无 `/api` 前缀）。
  - 前端默认基址：`EviQAsys/frontend/src/api/client.js:1` 默认 `API_BASE = "http://127.0.0.1:9075/api"`，与上面一致。

- 文档修订指引：
  - 将文档中未加前缀的接口路径（如 `POST /collections/{id}/documents`）统一改为带前缀的形式：`/api/collections/{id}/documents`、`/api/collections/{id}/documents?page=1` 等。
  - 保留健康检查为 `/healthz`（不加 `/api`）。
  - 若出现环境变量或反向代理示例，仅替换路径基前缀为 `/api`，主机与端口按部署环境自定。

备注：本修复仅涉及“API 基路径”文字说明对齐至当前代码实现；响应 envelope（成功 `{"code":"OK","data":...}`，错误 `{"code":"SOME_ERROR","message":"..."}`）与路由示例如需一并对齐，参见 M3_doc_consistency_check.md 第 1 条建议。

# 2  Evidence 编号策略冲突
统一改成 按 chat 连续，即“在同一 chat 下延续编号”
交互文档与示例答案中的锚点编号均按 chat 连续编号展示。

# 3 elements.order_start/order_end 含义与类型不一致
这个东西不是起止 element ID，而是起止的阅读顺序order_id
  - 表示阅读顺序索引：更名为 `order_start`/`order_end`，类型用 `INT`，语义为元素的 `order` 范围。

# 4 同步/异步流程表述冲突

- 统一按照 同步、无后台队列 设计
- 删掉所有后台、异步、轮询相关的设计

# 5 技术栈命名大小写不一致（React / DSPy）
  - 统一品牌名为 “DSPy”（pip 包名写作 `dspy`）；前端统一为 “React”。
  - 若需在文档中并列展示品牌名与包名，建议写法“DSPy（包名 `dspy`）”。

# 6 表名与标题大小写混用
  - 规范：表名统一小写（`turn2evidence`）；文档标题可写“Turn2Evidence（表）”，并在首次出现处注明实际表名。

# 7 外键级联与索引策略不一致

  - 统一 M1 策略：所有相关外键采用 `ON DELETE CASCADE`；
  - 数据库表性能索引先不建立， 等E2E流程全部跑完后再考虑。(比如针对doc_id列建索引等等)

# 10 向量维度配置说明中英文不一致
 - 在 docs/zh/数据模型.md 同步补充“向量维度通过环境变量 `VECTOR_DIM` 配置”的说明。

# 11  统一元素结构的字段命名与数据模型不一致
- 建议：
  - 统一采用数据模型中的命名：`image_base64`（图像内容，base64）与 `text_caption`（图/表的文字说明）。
  - 设计文档相应段落将 `image_content`/`image_caption` 改为 `image_base64`/`text_caption`，并在表格中保持“文本/图像/表格/公式”的一致字段组合描述。

