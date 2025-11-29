# M9 阶段计划（Chunk 检索升级 + Page-Chunk 可选二级检索）

## 1. 目标与背景
- 以 chunk 为主的索引/检索，去掉文本 overlap，提升召回精准度并保持回答阶段的元素锚点。
- 缩减 elements 表为渲染/锚点服务，新增 chunks 表承载向量与全文检索。
- 增设基于 PageTextChunk 的可选二级检索路径，在海量文档场景下用页级召回 + chunk 精选平衡效率与精度。

## 2. 范围与不做
- 范围：数据模型（elements 收缩、chunks 新表、page_text_chunks 可选表）、索引/检索/回答链路重构、配置与监控、文档同步。
- 不做：存量数据迁移（让用户重传）、前端交互形态变更（Evidence 编号/高亮保持）、自动化测试/CI。

## 3. 技术方案
### 3.1 数据模型
- elements：`text_content` 不再需要， 其他内容比如`raw_text_content`(不带导航前缀和overlap)、`order`与渲染元信息都要保留(image/table的caption仍然需要放到`raw_text_content` 中)；，`header` 不生成 summary，`equation` 保存文本与图片（嵌入仅用文本）。
- chunks（主索引表）：字段包含 `id/doc_id/collection_id/order/level_nav/chunk_text_main/elem_ids/page_start/page_end/elem_types/vec_embedding`，按 section 内顺序生成；image/table 强制单元素单 chunk，排在该 section chunk 列表末尾；允许元素跨页合并。 
- page_text_chunks（可选页级表）：每页聚合文本生成 `page_no` 级大 chunk，仅含文本向量（无多模态），字段包含`id/doc_id/collection_id/chunk_text_main/elem_ids/page_no/elem_types/vec_embedding`；用于二级检索的页过滤。

@todo chunk存elem_types， 那检索时如何指定特定类型的chunk进行检索？ 是否应该把chunk的type简化为image, table, text这3种类型，直接设置为chunk_type，在前端检索页面也这样简化展示，这是根据合并策略进行划分的。

### 3.2 索引与生成流程
- chunk builder：解析完成后触发，按 doc 读取 elements → 过滤空白/控制字符 → 在同一 `level_nav` 内按元素数量窗口合并（无 overlap）， → 直到遇到section边界 或者 字符数>= `MIN_CHARACTOR_CHUNK_SIZE`(优先判断) AND 合并的Elements个数达到`MAX_ELEM_CHUNK_SIZE`(前一个条件满足后才判断)时停止合并 → 写入 chunks → 触发 chunk 级嵌入（文本用 `chunk_text_main`，image/table 走图文联合路径）。
- page chunk builder（可选）：按 page_no 聚合文本元素生成 page_text_chunks，写入并向量化；规则与 chunk builder 同步的过滤开关。
- 重建：提供按 `collection_id/doc_id` 的重建入口，支持 chunk + 向量，包含页级表（若启用）。

### 3.3 检索与回答链路
- Chunk 一级检索：向量/全文检索直接命中 chunks，返回 `elem_ids/elem_types/level_nav/page_span`，去重同一 chunk。
- Page-Chunk 二级检索（可选开关）：前端暴露“一级/二级”模式；二级模式先在 page_text_chunks 上用问句向量检索页 topK（可选 doc_id 过滤），再限定 doc_id+page_no 到 chunks 做二次检索，返回同样的 chunk 结果格式。未开启时仅执行一级。
- 回答上下文：按 chunk 内元素顺序拼接 `"<elem_id> raw_text"` 送入 LLM；image/table chunk 用 caption/markdown 并保持图像取用路径；输出锚点仍为 `[Elem#<id>]`，写 turn2element 去重记录。
- DSPy/LLM 签名：输入调整为 chunk 文本列表并携带 `elem_ids`，提示模型仅引用提供的元素；检索路由/问句重写保持不变但入口替换为 chunk 级。
@todo 多个doc_id和多个page_no， 在chunk表上的查询会很复杂，而且对于一页而言，(doc_id,page_no)要作为一个元组放在filter中进行匹配。如果召回的页过多，将会出现大量的标量过滤器。 对于1个(:doc_id,:page_no)，在Chunk表中应该用 doc_id = :doc_id page_start <= :page_no AND :page_no <= page_end 来定位对应的Chunk。
curtodo

### 3.4 配置、监控与文档
- 配置：`MAX_ELEM_CHUNK_SIZE`、`MIN_CHARACTOR_CHUNK_SIZE`、`CHUNK_SKIP_PATTERNS`、`RETRIEVAL_TOPK_CHUNK`，新增页级检索开关与页级 topK（如 `RETRIEVAL_TOPK_PAGE`）；前端暴露二级检索开关。
- 文档：同步更新 `docs/zh/数据模型.md`、`多模态论文问答系统设计文档.md`、本阶段 dev log，说明新表与检索模式。

## 4. 开发拆解与里程碑
- 数据层：建 chunks 与 page_text_chunks 表；仓储接口与 schema；向量列迁移到 chunk；保留 elements 读取用于高亮。
- 索引链路：实现 chunk builder（过滤/窗口/落库/嵌入）；实现可选 page chunk builder；重建脚本/API。
- 检索链路：改为 chunk 主入口；实现二级检索逻辑（页级检索 → 受限 chunk 检索）；结果结构补充页面信息。
- 回答链路：上下文拼装切换到 chunk；锚点写 turn2element；保持 image/table VQA 路径。
- 前端与配置：提供一级/二级检索开关；配置项接入；结果展示兼容 chunk 锚点。
- 里程碑：① 数据/索引改造完成并能重建；② 检索/回答链路跑通 chunk 模式；③ 页级二级检索上线可控开关；④ 文档更新与手工验证完成。

## 5. 验证与交付
- 使用真实解析文档手工验证：chunk 生成统计、过滤效果、向量写入、chunk→元素映射正确；执行重建入口验证。
- 检索验证：对比一级与二级模式的命中页与答案合理性；检查 Evidence 编号、高亮链路正确。
- 交付：代码改造、配置示例、运维重建指引、更新后的设计/数据模型文档。

## 6. 风险与对策
- Chunk 过短/过长影响精度：通过 `MIN_CHARACTOR_CHUNK_SIZE` 与监控数据调优。
- 页级检索误召回：提供开关与 topK 可调，必要时保留直接 chunk 模式回退。
- 多模态嵌入一致性：image/table 单独成块且置于 section 末尾，避免文本窗口扰动；确保嵌入路径复用现有实现。
