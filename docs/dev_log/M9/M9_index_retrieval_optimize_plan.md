# M9 索引/检索精度优化方案（Chunk 化）

## 1. 背景与目标
- 现状：元素级检索在 `text_content` 上叠加 overlap、标题与导航信息，导致嵌入注意力被噪声稀释，检索召回精度下降。
- 目标：改为 section 内 element 合并的 chunk 级索引/检索，减少噪声、保留段落语义连续性，并让回答阶段能够精确绑定到元素。

## 2. 范围与不做
- 范围：后端数据模型、索引/检索服务、回答上下文拼装逻辑；文档/配置更新，去掉overlap机制。
- 不做：旧数据迁移（用户将重传文档）、前端交互形态变更（Evidence 编号/高亮机制保持）。

## 3. 数据结构调整
### 3.1 elements 表收缩
- `text_content` 不再作为检索目标；仅保留 `raw_text_content`（MinerU 原始文本）及元数据。
- `header` 元素不再生成/存储 summary，只保留标题原文（用于 chunk 组装时串联）。
- `equation` 仍在 elements 中保存图片/latex；chunk 合并时仅使用文本内容。
- 保留 `image_base64`、`text_caption`、`bbox_json` 等供渲染/图像问答，但不直接检索。

### 3.2 新增 chunks 表（向量与全文检索主表）
- 设计要点（字段级别，不含具体类型）：`id`, `doc_id`, `collection_id`, `order`（chunk 顺序，按 section 内遍历产生），`level_nav`，`chunk_text_main`（合并主体）、`elem_ids`（JSON 数组，保留元素顺序）, `page_start` ,`page_end` (合并进去的element的起止页面)，`elem_types`（用于前端指定检索 image/table/equation/text/head块，因为image和table只能单独成块，所以从检索element换成检索chunk后逻辑基本不变；特别的，equation类型表示这个chunk中包含equation/head类型的element；text则表示这个Chunk中只包含text类型的element），`vec_embedding`（文本/多模态向量）。
- 约束：chunk 生成仅限同一 `level_nav` 范围，不跨 section；`order` 在文档维度单调递增。
- 说明：`vec_embedding` 始终基于 chunk 级文本/多模态内容(对于非image/table 类型的chunk，直接使用`chunk_text_main`进行嵌入；对于image/table类型的chunk， 参照现有image/table类型的element，联合使用图片base64和`chunk_text_main`进行嵌入。)；elements 的向量列可废弃。

### 3.3 证据与关联
- 检索/回答阶段使用 chunk 作为召回单元，但回答文本仍输出 `[Elem#<id>]`，送给LLM前使用 `elem_ids` 将 chunk 映射回元素然后拼接。
- `turn2element` 继续以 element 维度落库；需要在回答阶段将每个命中的 chunk 内的元素 ID 去重后写入。
- 若后续需要 chunk 级统计，可增设 `turn2chunk`（目前非必需，暂不引入）。

## 4. Chunk 生成与过滤策略
### 4.1 入口与流程
- 解析完成写入 elements 后，在索引流程新增 `chunk_builder`：按 `doc_id` 读取有序 elements → 过滤无效元素 → section 内滑窗合并 → 写 chunks → 触发 chunk 级向量写入。
- 触发时机：上传解析成功后立即生成；后续若 chunk 规则/配置变动需支持按 `doc_id` 重建。

### 4.2 合并规则（文本侧）
- 合并单元：仅允许 `text` / `header` / `equation`。
- `chunk_size`：按元素个数（不按字符数）；同一 `level_nav` 内相邻元素按窗口合并。
- `overlap`：为了提高检索和回答的精度，我们在新版中不允许对文本进行overlap。
- `level_nav` 约束：窗口不可跨 section；section 边界处窗口截断。
- 拼装格式：主体文本阶段直接按elem_id顺序拼接raw_text即可，不要在拼接的文本中加入 `<elem_id>`。
- `header` 文本：直接使用 header 原文（无 summary），可放在窗口内相应位置。
- `equation`：使用 `raw_text_content`（LaTeX/文本），不携带图片到嵌入。
- `image` / `table` element要被作为独立的chunk，不与其他element合并，它们的顺序要放在它们所属的`level_nav`的chunk列表的最后(在该section中的所有Chunk中order最大)，然后它们相邻两侧的文本类型的element的合并不受影响。
- 允许element元素跨页合并。

### 4.3 特殊元素
- `image` / `table`：强制单元素单 chunk，不合并、不加 overlap；chunk 嵌入仍走“图文联合”路径（保留 caption + （table markdown） + image_base64 ）。
- chunk 内也有image_base64字段，只对 image/ table元素生效；equation在合并到chunk时不会带入它的图片(1个Chunk中允许合并进去多个equation)，`chunk_text_main` 仅含文本部分。

### 4.4 过滤启发式（需在代码中可配置开关）
- 跳过空白/仅空格/控制字符的 elements。

## 5. 检索策略调整
- 向量检索主索引改为 chunks；全文检索（keyword/highlight）亦对 chunks 运行。
- 召回时以 chunk 为单位返回；需要携带 `elem_ids`、`elem_types`、`level_nav`、`page_span`。
- 相似度排序：沿用现有阈值/归一化策略。
- 问句重写/路由逻辑保持不变，但检索入口替换为 chunk 级。
- 去重：同一 chunk 不重复返回

## 6. 回答上下文拼装
- 对检索到的 chunk，按照 `chunk_text_main` 中元素顺序拼成 `"<elem_id> raw_text"` 片段，送入 LLM。
- 对 image/table chunk：上下文文本为 caption/markdown；如需视觉问答，仍按现有路径使用 `image_base64` 取图，答案文本回注到该 chunk 的上下文后再送入 LLM。
- Anchoring：回答文本继续生成 `[Elem#<id>]`；需要在拼装上下文时提示模型仅引用 `elem_ids` 中出现的元素。
- Evidence 列表：从参与回答的 chunk 中提取元素集合 → 写 `turn2element` → API 侧动态生成 `evidence_no`（沿用现有前端渲染规范）。

## 7. OceanBase/后端落地点
- 新增 `chunks` 表及对应仓储（`repositories/chunks`）、schema、CRUD；向量列迁移到 chunk。
- 索引服务：`services/retrieval` 使用 chunk 仓储；同时保留元素读取能力用于高亮（通过 `elem_ids` 回查）。
- 流程编排：`services/qa_flow` 在解析后调用 chunk builder；问答链路从 chunk 检索节点开始。
- DSPy/LLM 签名：输入上下文字段改为 chunk 级文本列表，携带 `elem_ids` 以支持锚点输出。
- 文档更新：`docs/zh/数据模型.md`、`多模态论文问答系统设计文档.md` 需同步 chunk 架构。

## 8. 配置与运行
- 新增/调整配置：`CHUNK_SIZE_ELEMENTS`、`CHUNK_SKIP_PATTERNS`（启发式过滤）、`RETRIEVAL_TOPK_CHUNK` 、 `MIN_CHARACTOR_CHUNK_SIZE`(按字符计数控制最小chunk大小，如果chunk中的字符小于这个数目，则即使超过了`CHUNK_SIZE_ELEMENTS`，也继续往下合并，但是仍然不能跨越section合并。 即合并过程中优先满足不能跨section合并要求，其次满足字符数下限要求，最后满足`CHUNK_SIZE_ELEMENTS`的要求) 
- 重建索引流程：提供按 `collection_id/doc_id` 重建 chunk+向量的运维入口（脚本或 API），便于规则更新后重算。
- 监控：记录 chunk 生成计数、过滤掉的元素数量、平均 chunk 长度，便于验证规则效果。

## 9. 开发拆解
- 数据层：建表 SQL、仓储接口、迁移脚本（仅建表/字段，旧数据不迁移）。
- 索引链路：实现 chunk builder（过滤→窗口→落库→嵌入）、向量写入。
- 检索链路：重写检索入口为 chunk，返回结构补充 `elem_ids`/页面信息。
- 回答链路：上下文拼装切换到 chunk，锚点与 evidence 写入调整。
- 文档：更新数据模型与设计文档，补充配置说明。

## 10. 特别确认的问题
- 需要在整个系统层面去掉overlap，从而保证精准性。
- 视觉问答路径：图像 chunk 保持“按需触发VQA”的策略
- 过滤规则：不用对作者信息进行过滤(chunk_size设置得稍大，减少其占用的块数)。 
- Evidence 锚点：1个chunk 内不可能出现多张图/表，chunk在回答前会转化成element，引用时还是以element为单位做细粒度引用。

# 补充的检索流程要求

- 以上文档内容只要求基于Chunk表进行检索，我们称为Chunk一级检索。
- 为了在面对大量文档时可以提供平衡精度与效率的检索方式，我们希望进一步引入一个基于PageTextChunk的表进行检索，也就是在索引构建阶段按照page_no把每一页中的文本聚合起来成为一个大Chunk(以页为单位的文本Chunk)，这个Chunk不包含多模态信息，只包含文本信息，然后允许检索时根据doc_id检索topK个相关的页，然后根据这个页级的检索结果进一步地在Chunk表中限定doc_id和page_no检索指定的Chunk，从而提高在海量文档中的检索精度，这个称为Page-Chunk-二级检索。

