M3 文档一致性检查（仅阅读、未做修改）

范围：扫描 <WORK_DIR>/docs/ 下的 en/、zh/、dev_log/ 文档，聚焦接口契约、数据模型、流程与术语的跨文档一致性。

总体结论：发现若干高影响不一致，建议在 M3 收口时一次性对齐，避免后续实现与文档背离。

问题与建议（按优先级）

1) API 基路径与响应 envelope 不一致
- 表现：
  - 英文交互文档声明统一前缀 `/api` 且采用 `{ code:"OK", data }`：docs/en/backend_frontend_interactive_design.md:17,23-26,34-36。
  - 中文交互文档未带 `/api` 且 envelope 为 `{data, meta, error}`：docs/zh/前后端交互逻辑设计.md:21-24,32-34,84-91,105-121。
  - 开发路线图英文版个别示例遗漏 `/api` 前缀：docs/en/Develop_Road_Map.md:57（“POST /collections/{id}/documents”）。
- 建议：
  - 规范为：所有接口统一以 `/api` 为前缀；统一响应 envelope 为 `{"code":"OK","data":...}`；错误返回 `{"code":"SOME_ERROR","message":"..."}`。
  - 修改清单：
    - docs/zh/前后端交互逻辑设计.md：所有路径加 `/api/` 前缀；将“请求封装统一格式”样例改为 `{"code":"OK","data":...}`；顺序图内路径同步调整。
    - docs/en/Develop_Road_Map.md:57 与文内其余未加前缀的示例，补全为 `/api/...`。

2) Evidence 编号策略冲突（按 chat 连续 vs. 按 turn 重置）
- 表现：
  - 设计文档强调“在同一 chat 下延续编号”：docs/en/Design_Document.md:77。
  - 英文数据模型称“每个 turn 内从 1 开始”：docs/en/Data_Model.md:135；但同文又称“在每个 chat 内递增”：docs/en/Data_Model.md:155。
  - 中文数据模型同样存在“按 turn”与“按 chat”混用：docs/zh/数据模型.md:133 与 159。
  - `chats.max_evidence_no` 字段说明倾向于 chat 级连续编号：docs/en/Data_Model.md:89，docs/zh/数据模型.md:87。
- 建议（推荐采纳 chat 级连续编号）：
  - 将 Turn2Evidence 主键改为 `(chat_id, evidence_no)`；保留 `turn_id` 列，并加索引 `(turn_id, evidence_no)` 以便查询；或保留 `PRIMARY KEY (chat_id, evidence_no)` + 非唯一索引 `(turn_id)`。
  - 统一字段说明为“evidence_no 在 chat 内从 1 开始递增，不在每个 turn 重置”。
  - 交互文档与示例答案中的锚点编号均按 chat 连续编号展示。

3) elements.order_start/order_end 含义与类型不一致
- 表现：
  - 英文数据模型将其描述为“section 的起止 element ID”，但字段名带 `order_` 且类型为 VARCHAR：docs/en/Data_Model.md:69-70。
  - 中文数据模型写明“起始/结束元素id”，同为 VARCHAR：docs/zh/数据模型.md:68-69。
- 建议（两种做法二选一）：
  - 若表示阅读顺序索引：更名为 `order_start`/`order_end`，类型用 `INT`，语义为元素的 `order` 范围。
  - 若表示元素主键 ID：更名为 `element_id_start`/`element_id_end`，类型用 `BIGINT`。
  - 中英文文档同步修改命名与类型说明。

4) 同步/异步流程表述冲突
- 表现：
  - 蓝图与路线图强调同步、无后台队列：docs/en/Architecture_Blueprint.md:3,42-45,50,54；docs/en/Develop_Road_Map.md:71。
  - 交互文档却出现“异步解析/索引 + 轮询状态”流程：docs/en/backend_frontend_interactive_design.md:35；docs/zh/前后端交互逻辑设计.md:33。
- 建议：
  - M2/M3 阶段统一按同步实现，删除/弱化“状态轮询”步骤，或标注为“后续可选扩展（引入后台 Job 后启用）”。若保留异步方案，需在蓝图与路线图中一并补充说明。

5) 技术栈命名大小写不一致（React / DSPy）
- 表现：
  - 前端被写成“ReAct”，应为 React：docs/en/Tech_Stack.md:6；docs/zh/技术栈.md:5。
  - DSPy 混用大小写（DsPy/DsPY）：docs/en/Tech_Stack.md:10；docs/zh/技术栈.md:9。
- 建议：
  - 统一品牌名为 “DSPy”（pip 包名写作 `dspy`）；前端统一为 “React”。
  - 若需在文档中并列展示品牌名与包名，建议写法“DSPy（包名 `dspy`）”。

6) 表名与标题大小写混用
- 表现：标题用“Turn2Evidence”，表名用小写 `turn2evidence`，两者混用：多处文档均如此。
- 建议：
  - 规范：表名统一小写（`turn2evidence`）；文档标题可写“Turn2Evidence（表）”，并在首次出现处注明实际表名。

7) 外键级联与索引策略不一致
- 表现：
  - 英文数据模型明确 `ON DELETE CASCADE`：docs/en/Data_Model.md:46,77,116；中文数据模型写“级联或设为 NULL 视需求”：docs/zh/数据模型.md:44-45。
  - 英文数据模型将性能索引延后：docs/en/Data_Model.md:146；中文数据模型提前定义了 `idx_chat_turn`/`idx_turn_element`：docs/zh/数据模型.md:146-149。
- 建议：
  - 统一 M1 策略：所有相关外键采用 `ON DELETE CASCADE`；性能索引延后到后续里程碑，避免过早承诺与实现。

8) API 示例路径的 `/api` 前缀遗漏
- 表现：docs/en/Develop_Road_Map.md:57,169-171,150-156（部分示例行）存在未加 `/api` 的写法。
- 建议：统一补全为 `/api/...`，与交互文档和蓝图一致。

9) 术语与库名统一（dspy/DsPy/DSPy）
- 表现：跨文档混用多种写法：rg 统计见 docs/en/Architecture_Blueprint.md:22；docs/en/Develop_Road_Map.md:20,98,108,171；docs/en/dependency_tool_service.md:7；docs/zh/开发路线图.md:10,60,65,125；docs/zh/env_install.md:101。
- 建议：统一品牌名 “DSPy”，涉及 pip/导入处统一写 `dspy`。

10) 向量维度配置说明中英文不一致
- 表现：英文数据模型说明可通过 `VECTOR_DIM` 配置维度：docs/en/Data_Model.md:68；中文数据模型未提及。
- 建议：在 docs/zh/数据模型.md 同步补充“向量维度通过环境变量 `VECTOR_DIM` 配置”的说明。

11) 统一元素结构的字段命名与数据模型不一致
- 表现：
  - 设计文档“Unified Element Structure”使用 `image_content`/`image_caption` 表述：docs/en/Design_Document.md:46-55；
  - 数据模型使用 `image_base64` 与 `text_caption`：docs/en/Data_Model.md:63-66；docs/zh/数据模型.md:62-66。
- 建议：
  - 统一采用数据模型中的命名：`image_base64`（图像内容，base64）与 `text_caption`（图/表的文字说明）。
  - 设计文档相应段落将 `image_content`/`image_caption` 改为 `image_base64`/`text_caption`，并在表格中保持“文本/图像/表格/公式”的一致字段组合描述。

备注
- 本检查仅阅读与比对文档，未对代码或系统文件做任何修改。
- 如需，我可以按以上建议生成最小的修订补丁草案供审阅，再由您确认后落地。
