好，那我按“系统里只存 1 份 memory”的设定，重新整理一份给 ai coder 看得懂的实现文档。

---

# MemoryAgent 设计与实现规范（单一 memory 模型）

> 目标：系统中**每个 turn 只存一份 memory 文本**（turns.memory），通过长度限制 + LLM 总结来控制体积，并保证 `[Elem#id]` 引用的正确性。

---

## 1. 核心参数

* `MEMORY_MAX_LEN` / `max_memory_length = 4000`

  * 控制：**当前已有 memory + 本轮 Q/A 拼接后的长度上限**
  * 超过这个长度，就不再直接拼接，而是触发一次 LLM 总结。

* `max_summary_memory_length = 1000`

  * 控制：LLM 总结后的目标长度（**软限制**）
  * 只在提示词里说明，不需要对 LLM 输出做二次截断或校验。

系统里最终**只维护一份 `memory` 字段**（例如 turns 表的 `memory` 列），每轮会被覆盖更新。

---

## 2. 部分 A：记忆更新（memory_generation，用于 turn 写入）

### 2.1 输入与输出

* 输入：

  * `last_turn_memory`: 上一轮存储在 turns.memory 的文本（可能为空）
  * `question`: 当前轮的用户问题
  * `answer`: 当前轮 AnswerAgent 的答案

* 输出：

  * `new_memory`: 当前轮要写入 turns.memory 的最终文本

### 2.2 更新流程

伪代码示意：

```python
def update_memory(last_turn_memory: str, question: str, answer: str) -> str:
    # Step 1: 构造“直接拼接”版本
    candidate = concat_as_plain_text(last_turn_memory, question, answer)

    # Step 2: 如果长度未超限 → 直接使用
    if len(candidate) <= MEMORY_MAX_LEN:
        new_memory_raw = candidate
    else:
        # Step 3: 超限 → 调用 LLM 进行总结
        prompt = build_memory_summary_prompt(
            question=question,
            answer=answer,
            last_turn_memory=last_turn_memory,
            max_summary_memory_length=max_summary_memory_length,
        )
        new_memory_raw = call_llm(prompt)

    # Step 4: 对 new_memory_raw 做 [Elem#id] 校验与清洗
    new_memory = validate_and_clean_elem_ids(new_memory_raw)

    return new_memory
```

> 注意：
>
> * 没有“原始 memory + summary memory”两份数据，只有 1 个 `new_memory`。
> * 若触发总结，LLM 输出将**直接覆盖**上一轮 memory。

### 2.3 LLM 总结提示词（固定模板）

供 coder 直接拷贝使用（英文 prompt，插入变量即可）：

```text
Based on the current turn’s question, answer, and the previous turn’s memory,
generate an updated memory summary.

Requirements:
1. While compressing the content, you must retain all necessary `[Elem#id]` 
   references from the previous memory. Do NOT remove, rename, or alter them.
2. The new summary should be concise and highlight key information, dialog state,
   and essential evidence references across turns.
3. The total length should not exceed {max_summary_memory_length} characters.
   This is a soft limit; do your best to stay under it.
4. Output only the updated memory text with no extra commentary.

current turn question:
{question}

current turn answer:
{answer}

last turn memory:
{last_turn_memory}
```

**实现要点：**

* `{max_summary_memory_length}` 用实际数值替换（例如 1000）。
* 不需要对 LLM 返回结果再做长度校验或截断（完全按“软限制”处理）。
* LLM 输出必须当作**纯文本 memory** 使用，不能再包含额外说明、JSON 等结构。

### 2.4 `[Elem#id]` 校验与清洗逻辑

> ⚠ 这一段是对原需求中“入库前做正则验证”的明确工程化说明。

1. 使用正则，从 `new_memory_raw` 中匹配所有 `[Elem#xxx]`：

   * 示例正则（可根据真实 ID 格式微调）：

     ```python
     pattern = r"\[Elem#[0-9A-Za-z_-]+\]"
     ```
2. 去重后得到一组 `elem_ids`（如 `Elem#123`, `Elem#A_45`）。
3. 对每个 `elem_id` 调用数据库查询，检查该 element 是否存在：

   * 若不存在，则将 **该 `[Elem#id]` 文本从 memory 中删除**，其余文字保留。
4. 若有任何无效 id 被移除，在后端打印 warning log，建议包含：

   * 当前 turn_id 或 chat_id
   * 被移除的 `elem_id` 列表
   * 方便后续排查（例如模型输出了脏 ID）

伪代码示意：

```python
def validate_and_clean_elem_ids(memory_text: str) -> str:
    elem_tags = re.findall(r"\[Elem#[0-9A-Za-z_-]+\]", memory_text)
    invalid_tags = []

    for tag in set(elem_tags):
        elem_id = tag.strip("[]")  # "Elem#123"
        if not db_element_exists(elem_id):
            invalid_tags.append(tag)

    cleaned = memory_text
    for tag in invalid_tags:
        cleaned = cleaned.replace(tag, "")

    if invalid_tags:
        logger.warning(
            "Memory contains invalid Elem IDs, removed them.",
            extra={"invalid_elem_tags": invalid_tags}
        )

    return cleaned
```

最后写入 turns 表的就是 `cleaned` 之后的 `new_memory`。

---

## 3. 部分 B：记忆检索（memory_selection，用于生成 evidence）

> 用于“从 memory 里捞出对当前 question 有用的 evidence element”。

### 3.1 输入与输出

* 输入：

  * `question`: 当前 turn 的 question
  * `last_turn_memory`: 上一轮存储在 turns.memory 的文本（已经是处理过的版本）

* 输出：

  * `memory_text_elements`: 从 memory 中选出来的、对当前问题有帮助的文本元素列表
  * `memory_image_elements`: 对当前问题有帮助的图片元素列表

    * 若 `use_image = false` → 直接丢弃/返回空列表

### 3.2 检索流程（高层逻辑）

1. 调用 LLM，让它**从 memory 文本中抽取有用的 element_id 列表**：

   * 输入是 `question + last_turn_memory`
   * 输出是若干 `[Elem#id]`（具体 prompt 由另外的 MemoryAgent 设计文档决定，这里不展开）

2. 对 LLM 抽取出的 `[Elem#id]` 再做一次 **存在性校验**：

   * 与 2.4 的逻辑类似：

     * 不存在 → 丢弃该 id 并打 warning log。

3. 根据有效的 `elem_id` 集合，从数据库中加载对应 elements：

   * 文本类 → 加入 `memory_text_elements`
   * 图片类 → 加入 `memory_image_elements`

4. 若 `use_image = false`：

   * `memory_image_elements = []`
   * 或者在更上游就直接不对图片类 id 做检索。

---

## 4. Coder 实现 Checklist

### 4.1 记忆更新（memory_generation）

* [ ] 只维护一份 `memory`，存储在 turns 表的 `memory` 列
* [ ] 每轮更新时，先尝试 `last_turn_memory + 当前 Q/A` 直接拼接
* [ ] 若长度 ≤ `MEMORY_MAX_LEN` → 直接当作 `new_memory_raw`
* [ ] 若长度 > `MEMORY_MAX_LEN` → 使用固定 prompt 调用 LLM 总结生成 `new_memory_raw`
* [ ] 不再对 LLM 输出长度做硬校验 / 截断，只依赖 prompt 的软限制
* [ ] 对 `new_memory_raw` 里所有 `[Elem#id]` 做存在性校验，移除不存在的 id，并打印 warning
* [ ] 将清洗后的文本写入 turns.memory

### 4.2 记忆检索（memory_selection）

* [ ] 输入：`question + last_turn_memory`
* [ ] 使用 LLM 从 memory 文本中抽取与当前问题相关的 `element_id`
* [ ] 对这些 `element_id` 做存在性校验，丢弃无效 id，并打 warning
* [ ] 查询数据库，按 type 拆成 `memory_text_elements` 与 `memory_image_elements`
* [ ] 若 `use_image = false`，对图片部分直接置空或跳过

---

如果你愿意，我可以下一步帮你把这一套规则**翻译成具体的 dspy 模块接口设计**（比如 `class MemoryAgent(dspy.Module): ...` 的输入输出定义与伪实现），方便你直接丢给本地 Cursor 去写代码。
