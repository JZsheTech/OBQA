# M9 阶段计划（Chunk 检索升级 + Page-Chunk 可选二级检索）

## 1. 目标与背景
- 以 chunk 为主的索引/检索，去掉文本 overlap，提升召回精准度并保持回答阶段的元素锚点。
- 以chunk为单位检索，返回给LLM回答和前端显示时仍然将chunk映射回element(通过elem_ids)
- 缩减 elements 表为渲染/锚点服务，新增 chunks 表承载向量与全文检索。
- 增设基于 PageTextChunk 的可选二级检索路径，在海量文档场景下用页级召回 + chunk 精选平衡效率与精度。

## 2. 范围与不做
- 范围：数据模型（elements 收缩、chunks 新表、page_text_chunks 可选表）、索引/检索/回答链路重构、配置与监控、文档同步。
- 不做：存量数据迁移（让用户重传）、前端交互形态变更（Evidence 编号/高亮保持）、自动化测试/CI。

## 3. 技术方案
### 3.1 数据模型
- elements：`text_content` 不再需要，其他内容比如 `raw_text_content`(不带导航前缀和 overlap)、`order` 与渲染元信息都要保留（image/table 的 caption 仍然需要放到 `raw_text_content` 中）；`header` 不生成 summary，`equation` 保存文本与图片（合并到chunk中时仅用文本）。
- chunks（主索引表）：字段包含 `id/doc_id/collection_id/order/level_nav/chunk_type/chunk_text_main/elem_ids/page_start/page_end/vec_embedding`，按 section 内顺序生成；`chunk_type` 仅三类 {text, image, table}，按合并策略决定，image/table 强制单元素单 chunk 且放在该 section chunk 列表末尾；允许元素跨页合并。前端检索展示与过滤同样基于 `chunk_type`，不再存储逐元素类型列表。
- page_text_chunks（可选页级表）：每页聚合文本生成 `page_no` 级大 chunk，仅含文本向量（无多模态），字段包含 `id/doc_id/collection_id/chunk_text_main/elem_ids/page_no/chunk_type/vec_embedding`，其中 `chunk_type` 固定为 text；用于二级检索的页过滤，规则与 chunk builder 同步的过滤开关。

### 3.2 索引与生成流程
- chunk builder：解析完成后触发，按 doc 读取 elements → 过滤空白/控制字符 → 在同一 `level_nav` 内按元素数量窗口合并（无 overlap）， → 直到遇到 section 边界或者字符数 >= `MIN_CHARACTOR_CHUNK_SIZE`(优先判断) AND 合并的 Elements 个数达到 `MAX_ELEM_CHUNK_SIZE`(前一个条件满足后才判断)时停止合并 → 写入 chunks（落库时写明 `chunk_type`）→ 触发 chunk 级嵌入（文本用 `chunk_text_main`，image/table 走图文联合路径）。
- page chunk builder（可选）：按 page_no 聚合文本元素生成 page_text_chunks，写入并向量化；规则与 chunk builder 同步的过滤开关。
- 重建：提供按 `collection_id/doc_id` 的重建入口，支持 chunk + 向量，包含页级表（若启用）。

### 3.3 检索与回答链路
- Chunk 一级检索：向量/全文检索直接命中 chunks，返回 `chunk_id/elem_ids/level_nav/page_span/chunk_type`，去重同一 element，前端可按 `chunk_type` 过滤展示。
- Page-Chunk 二级检索（可选开关）：前端暴露“一级/二级”模式；二级模式先在 page_text_chunks 上用问句向量检索页 topK（可选 doc_id 过滤），得到 (doc_id, page_no) 元组列表，产生一串下面形式的标量过滤器(每个元组对应1个过滤器，外层用OR连接)： `doc_id = :doc_id AND page_start <= :page_no AND :page_no <= page_end` ，然后以这一串过滤器作为标量过滤条件在Chunk表中做向量检索，再返回同样的 chunk 结果格式。未开启时仅执行一级。
- 回答上下文：按 chunk 内元素顺序拼接 `"<elem_id> raw_text"`(对element去重) 送入 LLM；image/table chunk 用 caption/markdown 并保持图像取用路径；输出锚点仍为 `[Elem#<id>]`，写 turn2element 去重记录。
- DSPy/LLM 签名：输入不变，仍然是element级别；检索路由/问句重写保持不变；检索得到的结果的Chunk级别到Element级别的转换由retrieve相关的接口内部完成，retrieve对外的接口仍然是query -> element_list 而不是 query -> chunk_list

### 3.4 配置、监控与文档
- 配置：`MAX_ELEM_CHUNK_SIZE`、`MIN_CHARACTOR_CHUNK_SIZE`、`CHUNK_SKIP_PATTERNS`、`RETRIEVAL_TOPK_CHUNK`，新增页级检索开关与页级 topK（如 `RETRIEVAL_TOPK_PAGE`）；前端暴露二级检索开关与 `chunk_type` 过滤，并允许用户设置`RETRIEVAL_TOPK_CHUNK`、 `RETRIEVAL_TOPK_PAGE`。
- 文档：同步更新 `docs/zh/数据模型.md`、`多模态论文问答系统设计文档.md`、本阶段 dev log，说明新表与检索模式。

## 4. 开发拆解与里程碑
- 数据层：建 chunks 与 page_text_chunks 表；仓储接口与 schema；向量列迁移到 chunk；保留 elements 读取用于高亮。
- 索引链路：实现 chunk builder（过滤/窗口/落库/嵌入）；实现可选 page chunk builder；重建脚本/API。
- 检索链路：改为 chunk 主入口；实现二级检索逻辑（页级检索 → 受限 chunk 检索）；结果结构补充页面信息与 chunk_type。
- 回答链路：上下文拼装切换到 chunk；锚点写 turn2element；保持 image/table VQA 路径。
- 前端与配置：提供一级/二级检索开关；配置项接入；结果展示仍然显示element锚点， 检索时允许通过 chunk_type 筛选模态类型。
- 里程碑：① 数据/索引改造完成并能重建；② 检索/回答链路跑通 chunk 模式；③ 页级二级检索上线可控开关；④ 文档更新与手工验证完成。

## 5. 验证与交付
- 使用真实解析文档手工验证：chunk 生成统计、过滤效果、向量写入、chunk→元素映射正确；执行重建入口验证。
- 检索验证：对比一级与二级模式的命中页与答案合理性；检查 Evidence 编号、高亮链路正确；按 chunk_type 过滤时行为合理。
- 交付：代码改造、配置示例、运维重建指引、更新后的设计/数据模型文档。

## 6. 风险与对策
- Chunk 过短/过长影响精度：通过 `MIN_CHARACTOR_CHUNK_SIZE` 与监控数据调优。
- 页级检索误召回或过滤爆炸：提供开关与 topK 可调，二级检索使用 doc_id + page 范围过滤。
- 多模态嵌入一致性：image/table 单独成块且置于 section 末尾，避免文本窗口扰动；确保嵌入路径复用现有实现。
