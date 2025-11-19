
# M4：元素结构与上下文处理优化计划（draft）

> 目标：在不破坏现有接口和检索链路的前提下，系统性优化 `documents` / `elements` 数据的解析与存储逻辑，使得：
> - `level_nav` 表达完整且可读的章节路径；
> - `text_content` 作为“独立检索实体”包含足够的上下文（论文标题 / 页码 / 章节路径 / 前后文片段）；
> - 新增 `raw_text_content` 字段保留 MinerU 原始文本，方便调试与重构；
> - `documents.title` 与 Evidence 元数据与论文实际结构保持一致；
> - M2/M3/M4 文档规范与实际实现完全对齐。

本计划仅是实现指南，不直接改动代码；后续由 AI coder / 人类开发按阶段执行，并在对应文档中更新“已完成”标记。

---

## 0. 背景与现状梳理

### 0.1 当前实现位置

- DB 结构：`EviQAsys/backend/app/repositories/sql/schema.sql`
  - `documents`：`title / md_text / file_* / num_pages / element_count`
  - `elements`：`elem_type / header_name / header_level / level_nav / text_content / text_caption / image_base64 / bbox_json / page_no / order / order_start / order_end / vec_embedding`
- 解析与标准化：
  - 标题层级与导航：
    - `EviQAsys/backend/app/services/parser/header_processor.py`
      - `preprocess_headers(content_list)`：计算 `elem_type/header_level/header_name/level_nav/order_start/order_end`
      - 目前 `HEADER_NUMBER_PATTERN` 仅支持数字编号（如 `1.2.3`），`_build_nav_token` 会对标题文本做 `lower()`。
  - 元素归一化：
    - `EviQAsys/backend/app/services/parser/unifier.py`
      - `normalize_element(item, images=...)`：
        - 构造前缀：`prefix = f"[{level_nav}] [{header_name}]"`；
        - `_build_text_content(elem_type, prefix, item)`：
          - `text`：`prefix + text`
          - `header`：`prefix + section_summary`
          - `image`：`prefix + (image_caption or "[figure]")`
          - `table`：`prefix + (table_caption + table_body)`
          - `equation`：`prefix + (text or latex)`
        - `_extract_caption` 已经对 `table` 做了 `caption` 聚合。
- 文档入库：
  - `EviQAsys/backend/app/services/ingestion/document_ingestor.py`
    - `_ingest_stored_file`：
      - 目前 `documents.title = Path(stored.original_name).stem`
      - 调用 `MinerUAdapter.parse` → `content_list/images/md_text`
      - `preprocess_headers` → `_attach_header_summaries`（TF-IDF 生成 `section_summary`）
      - `normalize_element` → `elements_repo.batch_insert`
- 配置：
  - `EviQAsys/backend/app/env_setting.py`：`VECTOR_DIM / INGEST_BATCH_SIZE / ...`
- QA flow / Evidence：
  - `EviQAsys/backend/app/services/qa_flow/qa_orchestrator.py`
  - `EviQAsys/backend/app/services/mapping/evidence_mapper.py`
  - `EviQAsys/backend/app/services/memory/memory_service.py`

### 0.2 已知问题总结

1. **`level_nav` 不包含完整父级路径**  
   - 期望：`1. introduction > 1.1 GNN > 1.1.1 message passing`  
   - 实际：部分场景只保留叶子节点，且存在 `root` 虚拟节点与小写化问题。

2. **`text_content` 前缀设计老化**  
   - 当前统一为：`[level_nav] [header_name] + body`，`header_name` 与 `level_nav` 信息重复。
   - 不能体现：
     - 所属文档（document_title）；
     - 页码（page_no）；
     - 前后文上下文（overlap）。

3. **表格元素文档与实现不一致**  
   - 文档：图像/表格：`text_content = header_name + level_nav + text_caption`。  
   - 实现：表格已经使用 `caption + table_body`，更合理，但与设计文档不一致。

4. **`documents.title` 解析不符合论文场景**  
   - 当前直接使用 PDF 文件名作为标题，丢失 MinerU 已解析好的论文主标题。

5. **元素级上下文（overlap）缺失**  
   - `text_content` 只包含当前元素内容，缺少前后邻近元素的文本上下文，影响检索与回答的局部连贯性。

6. **标题层级解析缺乏对字母编号的支持**  
   - 附录中常见的 `c.3`、`Appendix A.1.2` 等模式目前没有明确支持策略。

7. **文档规范与真实实现存在偏差**  
   - 多处文档仍使用旧规范：`[level_nav] [header_name] + ...`；
   - Evidence 元数据中尚未统一体现 `[doc_title] [page_no] [level_nav]`。

---

## 1. 统一规范（基于本轮确认）

本小节给出后续实现应遵循的**目标规范**，后续章节将按模块拆解实现步骤。

### 1.1 `level_nav` 规范

1. **范围与内容**
   - 起点：从文内第一个真正的 header 开始，`level_nav` 不再出现 `root`。
   - 内容：只包含章节路径（多级标题），**不包含整篇论文标题**；论文标题出现在 `text_content` 前缀中。
2. **格式**
   - 章节间使用 `" > "` 分隔：`"1. Introduction > 1.1 GNN > 1.1.1 Message Passing"`。
   - 不额外包裹方括号；方括号仅用于 `text_content` 前缀。
3. **大小写**
   - 保留原始标题文本的大小写，只做空白压缩与基本清洗，不做 `.lower()`。
4. **字母编号支持**
   - 数字编号延续原逻辑：`1.` → level 1，`1.2.` → level 2，依此类推。
   - 字母编号规则：
     - `c.` 视为 level 1；
     - `c.3` 视为 level 2（点的个数 + 1）；
     - 扩展支持：`Appendix A`（单层）、`Appendix A.1`、`Appendix A.1.2` 等常见模式，均能生成稳定的 `header_level` 与 `level_nav`。

### 1.2 `text_content` 统一格式

1. **前缀整体结构**
   - 统一采用“方括号 + key=value”的形式：
     - `text_content = "[doc={document_title}] [page_no={page_no}] [nav={level_nav}] " + {上下文文本}`
   - 其中：
     - `document_title` 来自 `documents.title`（参见 1.4 节规范）；
     - `page_no` 使用 **1-based** 的页码（当前 DB 字段）；
     - `level_nav` 按 1.1 节规范生成。

2. **正文内容拆分**
   - 设：
     - `raw_text_content`：该元素自身的“原始文本内容”；
     - `prev_raw_text_content_list`：同一 `level_nav` 且位于当前元素之前的若干元素 `raw_text_content`；
     - `succ_raw_text_content_list`：同一 `level_nav` 且位于当前元素之后的若干元素 `raw_text_content`。
   - 则：
     - `上下文文本 = "[PREV_CTX]\n" + prev_ctx + "\n[CURR]\n" + raw_text_content + "\n[NEXT_CTX]\n" + next_ctx`
   - 其中：
     - `prev_ctx = "\n\n".join(prev_raw_text_content_list)`；
     - `next_ctx = "\n\n".join(succ_raw_text_content_list)`；
     - 如果前/后文为空，则对应 block 可以省略或只保留标签与空行（具体实现时可选“无内容则跳过标签”）。

3. **不同元素类型的 `raw_text_content` 定义**
   - text：
     - `raw_text_content = MinerU content_list` 中的原始 `text` 字段；
     - 不附加任何 `document_title/level_nav/page` 前缀，也不包含 overlap。
   - header：
     - `raw_text_content` = header 的原始标题文本（经 `_clean_text` 去除多余空白）；
     - `section_summary` 继续单独用于 header 元素 `text_content` 的“主体部分”（即可作为 `raw_text_content` 的替代，但为了简单，本版规范指定 `raw_text_content` 仅存标题原文）。
   - image：
     - `raw_text_content = image_caption`（聚合后的文本）。
   - table：
     - `raw_text_content = table_caption + table_body(markdown)`；
     - 允许与 `text_caption` 部分重复，`raw_text_content` 更偏向调试与上下文拼接。
   - equation：
     - `raw_text_content = MinerU content_list` 中的 `"text"` 字段（通常为 LaTeX 文本）；若将来出现 `latex` 字段，可视情况扩展。

4. **`header_name` 在 `text_content` 中不再单独拼接**
   - 由于 `level_nav` 已包含当前 section 的标题信息，不再单独追加 `header_name`，避免重复。

### 1.3 `raw_text_content` 字段（DB 层）

1. **新字段命名与类型**
   - 在 `elements` 表中新增字段：
     - `raw_text_content`：推荐类型为 `MEDIUMTEXT`（至少为 `TEXT`），与 `text_content` 一致，避免长文截断。
2. **用途限定**
   - 仅用于：
     - 调试（如定位某个元素对应 MinerU 的原始文本）；
     - 构造 overlap 上下文（`prev_raw_text_content_list` / `succ_raw_text_content_list`）；
   - embedding 与向量检索一律基于增强后的 `text_content`。

### 1.4 `documents.title` 规范

1. **标题选择顺序**
   - 优先来源：`preprocess_headers` 之后，列表中第一个 `elem_type == "header"` 元素的 `header_name`；
   - 若该 header 文本为空或为 `'root'` 等占位符，则回退到 `Path(stored.original_name).stem`。
2. **清洗规则**
   - 使用 `_clean_text` 做空白压缩，去除前后空格；
   - 如有多行或尾部标点（如多余句号），可以保留，不做激进修改（避免破坏论文原名）。
3. **无 header 场景**
   - 若 MinerU 未解析出任何 header（极少数情况），统一回退到文件名（不抛异常）。

### 1.5 overlap 规则（上下文增强）

1. **环境变量**
   - 新增：
     - `ELEMENT_CONTEXT_OVERLAP`（int）：
       - 默认值：`1`（表示前后各 1 个元素）；
       - `0` 表示关闭 overlap（仅保留当前元素的 `raw_text_content`）。
2. **section 边界**
   - “不能跨 section”的精确定义：
     - 采用方案 B：要求候选前后元素的 `level_nav` 与当前元素 **完全相等** 才算同一 section。
3. **页边界**
   - 只要 `level_nav` 相同，即使跨页也允许 overlap；页码不作为截断条件。
4. **元素类型**
   - 允许 `text/image/table/equation/header` 混合进入前后文列表，只要 `level_nav` 相同；
   - 实现上可以按“按顺序选取在同一 section 内的相邻元素”的简单策略。

### 1.6 Evidence 与前端展示

1. **后端 Evidence 元数据**
   - 针对每个被命中的 element，后端在 evidence 数据包中应统一暴露：
     - `element_id`
     - `doc_id`
     - `page_no`
     - `elem_type`
     - `bbox_json`
     - `level_nav`
     - `[doc_title] [page_no] [level_nav]` 组合成的“可读标题串”（例如 `evidence_title` 字段）。
2. **前端使用**
   - 前端在 Evidence 渲染时，用该组合串作为“元素归属信息”的主要展示来源，与 `text_content` 前缀保持一致。

3. **文档规范**
   - M2/M4 相关文档中，所有旧的“`[level_nav] [header_name] + ...`”描述统一替换为：
     - “`[doc_title] [page_no] [level_nav] + ...`” 这一类更新规范。

---

## 2. 实现步骤拆解（代码侧）

本节按推荐执行顺序列出代码重构步骤，供后续迭代使用。

### 2.1 DB 模式 & 数据模型同步（raw_text_content + 文档修正）

**目标**：在不破坏现有数据的前提下，为 `elements` 增加 `raw_text_content` 字段，并同步数据模型文档。

1. 修改 `schema.sql`
   - 在 `elements` 表定义中新增：
     - `raw_text_content MEDIUMTEXT`（或 TEXT，根据最终决定）；
   - 确认是否需要兼容性 `ALTER TABLE` 片段（参考 `md_text/file_sha256/file_size_bytes/element_count` 的增量写法）。
2. 更新数据模型文档
   - `docs/zh/数据模型.md`：
     - 在 `elements` 表字段列表中新增 `raw_text_content` 描述；
     - 更正 `text_content` 说明为“包含 doc_title/page_no/level_nav + 原始文本 + overlap 上下文”。
   - `docs/zh/多模态论文问答系统设计文档.md`：
     - 修正“统一元素结构”小节，替换旧公式：
       - `header_name + level_nav + ...` → `[doc_title] [page_no] [level_nav] + ...`
     - 针对表格元素明确包含 markdown 文本。

### 2.2 标题层级与 level_nav 修正（header_processor）

**目标**：生成完整、可读、支持字母编号的 `level_nav`，并去掉 `root` 虚拟根与多余小写化。

1. `header_processor.py` 调整点：
   - 修改 `_clean_text`：
     - 保持现有“空白压缩”逻辑；
     - 确保不将文本转换为小写。
   - 扩展 `_build_nav_token`：
     - 保留原始大小写；
     - 扩展 `HEADER_NUMBER_PATTERN`，支持：
       - 数字编号（`1.2.3`）；
       - 字母编号（`c.3`、`A.1.2`）；
       - `Appendix A` / `Appendix A.1` / `Appendix A.1.2` 等模式。
     - 在无法解析编号时，退化为“清洗后的标题全文”。
   - 去除 `ROOT_LEVEL_NAV` 在正常路径中的使用：
     - 对于没有任何 header 的文档，保留 `root` 占位；
     - 一旦遇到第一个 header，后续元素的 `level_nav` 一律按 header 栈生成，不再出现 `root`。
2. 确认 `order_start/order_end` 逻辑不受影响（仍用于 section 文本聚合）。

### 2.3 文档标题提取（DocumentIngestor）

**目标**：让 `documents.title` 与论文首个 header 标题一致。

1. 在 `_ingest_stored_file` 中：
   - 在调用 `preprocess_headers` 之后，基于 `processed_items` 中第一个 `elem_type == "header"` 元素的 `header_name` 更新 `document["title"]`；
   - 若无 header 或 header_name 无效（空 / `root`），保留文件名 stem 作为标题；
   - 通过 `documents_repo.update_document` 将最终标题写回 DB（或在创建时就用解析出的标题）。
2. 更新相关文档：
   - 在设计文档与数据模型中说明 `documents.title` 的来源规则。

### 2.4 元素标准化重构：raw_text_content + 新 text_content

**目标**：将 `normalize_element` 拆分为“原始内容构造”和“上下文封装”两步，便于 overlap 等后续扩展。

1. `unifier.py`：增加 `raw_text_content` 构造
   - 在 `normalize_element` 中：
     - 引入 `_build_raw_text_content(elem_type, item)`，返回本元素的 `raw_text_content`，按 1.2 节定义；
     - 将结果写入返回 dict 中：
       - `"raw_text_content": raw_body`
     - `text_content` 暂时可以继续采用旧逻辑（`prefix + body`），但要删除 `header_name` 冗余（可作为过渡阶段）。
2. 在 `DocumentIngestor._ingest_stored_file` 中集中构造新 `text_content`
   - 思路：**将构造 overlap + 新前缀的逻辑从 `normalize_element` 挪到 ingestion 层**，因为这里可以看到完整的元素列表：
     1. 使用 `normalize_element` 得到基础元素列表（含 `raw_text_content/page_no/level_nav/header_name/...`）。
     2. 读取 `documents.title` 作为 `document_title`。
     3. 读取 `ELEMENT_CONTEXT_OVERLAP` 环境变量。
     4. 遍历元素列表，对每个元素：
        - 在同一 `level_nav` 范围内，按 `order` 查找前后各 `overlap` 个元素的 `raw_text_content`；
        - 生成 `prev_ctx` / `next_ctx` 字符串；
        - 构造新的 `text_content`：
          - `f"[doc={document_title}] [page_no={page_no}] [nav={level_nav}] ..."`
        - 覆盖 `row["text_content"]`。
3. 过渡策略
   - 为降低一次性改动风险，可分两步：
     - 第一步：只引入 `raw_text_content` 字段与新前缀（doc/page/nav），不启用 overlap；
     - 第二步：再打开 overlap 逻辑（受环境变量控制），并在 M4 测试中重点回归。

### 2.5 表格元素规范化与文档修正

**目标**：使“表格元素的文本表示”在代码与文档中完全一致。

1. 代码侧（如 2.4 所述）：
   - `_build_raw_text_content` 中，表格：
     - `raw_text_content = table_caption + table_body(markdown)`；
   - `text_caption` 字段继续保留 caption，用于 UI/Evidence 快速展示。
2. 文档侧：
   - `docs/zh/多模态论文问答系统设计文档.md`：
     - 将“图像/表格”的描述调整为：
       - 图像：`text_content` 使用 caption + 上下文；
       - 表格：`text_content` 使用 caption + markdown 表格文本 + 上下文。

---

## 3. Evidence 与前端集成改造计划

**目标**：保证前端在展示 Evidence 时，能直接利用 `[doc_title] [page_no] [level_nav]` 这一组信息，无需重复解析 `text_content`。

1. 后端 Evidence 映射
   - 核查 `evidence_mapper.py`、`qa_orchestrator.py`、`memory_service.py` 中的元素选取与返回结构：
     - 确保内部查询 `elements` 时至少取出：
       - `id/doc_id/page_no/elem_type/bbox_json/level_nav/text_content/raw_text_content`
   - 在 evidence 输出结构中新增字段（命名待定，例如 `evidence_title` 或 `nav_label`）：
     - `f"[doc={document_title}] [page_no={page_no}] [nav={level_nav}]"`；
   - 在 M4 文档中注明：前端应优先使用该字段作为 Evidence 的“位置描述”。
2. 前端配合调整（只在计划中标注，不在本阶段改代码）
   - Evidence 卡片上的“文档标题 + 页码 + 章节路径”展示来自新字段；
   - `answer_text` 中的 `[Elem#id]` 映射逻辑不变。

---

## 4. 测试与验证计划（手工）

**注意：遵守仓库测试规范，不使用 pytest，所有测试脚本为手工执行。**

1. 解析与入库验证
   - 使用已有手工脚本：
     - `EviQAsys/backend/tests/manual/test_m2_ingest.py`（如需，按新字段轻量扩展打印内容）；
   - 针对示例 PDF：
     - `sample_data/test_convert/1-Cui et al. - 2019 - Class-Balanced Loss Based on Effective Number of Samples/...`
   - 校验点：
     - `documents.title` 是否为论文真实标题（非文件名）；
     - `elements.level_nav` 是否为完整路径，无多余 `root`，大小写合理；
     - `elements.raw_text_content` 是否符合各类型定义；
     - `elements.text_content` 前缀是否为 `[doc=...] [page_no=...] [nav=...]`，且没有重复的 `header_name`。

2. overlap 验证
   - 在设置 `ELEMENT_CONTEXT_OVERLAP=1` 的情况下重新 ingest：
     - 检查某一 section 内连续元素的 `text_content`，是否包含前后元素的 `raw_text_content`；
     - 确认不同 `level_nav` 的元素之间没有越界合并。

3. QA flow 与 Evidence 验证
   - 使用：
     - `EviQAsys/backend/tests/manual/test_m4_qa_flow.py`
     - `EviQAsys/backend/tests/manual/test_m4_multi_turn_qa_flow.py`
   - 校验点：
     - 检索命中的元素，其 Evidence 数据中是否带有 `[doc_title] [page_no] [level_nav]` 组合字段；
     - 前端日志或 API 响应中，该字段能指导 Evidence 渲染与 PDF 高亮（人工检查）。

---

## 5. 文档同步与清理计划

在代码改动完成后，需要同步更新以下文档，确保“规范即实现”：

1. `docs/zh/数据模型.md`
   - 更新 `documents` / `elements` 表字段定义；
   - 明确 `text_content` / `raw_text_content` 的用途与差异。
2. `docs/zh/多模态论文问答系统设计文档.md`
   - 修改统一元素结构定义；
   - 补充 overlap 与 Evidence 相关说明。
3. `docs/zh/开发路线图.md`
   - 在相关里程碑（M2/M4）下追加“元素结构优化已完成”的简短描述。
4. `docs/dev_log/M2/*.md`、`docs/dev_log/M4/*.md`
   - 在计划/结果文档中标记：
     - 老的 `header_name + level_nav + ...` 规范已废弃；
     - 新规范 `"[doc=...] [page_no=...] [nav=...] + ..."` 已生效。

---

## 6. 迭代与兼容性建议

1. **分阶段开关策略**
   - 阶段 1：仅引入 `raw_text_content` + 新 `documents.title` 逻辑，不改变 `text_content` 格式；
   - 阶段 2：切换 `text_content` 前缀为 `[doc=...] [page_no=...] [nav=...]`，仍不启用 overlap；
   - 阶段 3：开启 `ELEMENT_CONTEXT_OVERLAP`，实施前后文合并；
   - 每个阶段完成后在 `M4_result.md` 中记录实测效果与潜在问题。

2. **兼容旧数据**
   - 对已有 `elements` 记录，若需要升级，可另写一条手工迁移脚本：
     - 读取旧 `text_content`，尽量还原 `raw_text_content`；
     - 重算新 `text_content`；
   - 也允许“只对新 ingest 的文档生效”，由业务方评估。

3. **对下游组件的影响评估**
   - Retrieval 服务：
     - 向量生成仍基于 `text_content`，但其内容结构更复杂，需要确认是否对 embedding 模型有明显影响（可在 M4 测试中观察）。
   - DSPy 组件：
     - `text_content` 更长，但仍以文本为主；可视需要在 prompt 中截断或加强说明标签（如 `[CURR]` 等）。

> 以上为 M4 元素处理优化的整体计划。后续 AI coder 在实现某一子任务时，应在对应小节下记录实际改动点和验证结论，保持计划与实现的双向同步。 
