# **《多模态论文问答Agent模块（简化版）设计文档》**

（定性描述 · 无代码细节 · 含伪代码形式流程图）

---

# 1. **整体工作流概述**

用户向系统提出一个问题，系统基于历史对话、论文集合、文本元素与图片元素进行检索、推理，最终给出一个包含 evidence 的回答。

流程被划分为两类组件：

### **A. DSPy 模块（文本↔文本的智能决策）**

用于：

* 对话记忆摘要
* 检索判别
* 问句重写
* 图像子问题生成
* 最终回答合成

### **B. 普通 Python 函数（工程类任务）**

用于：

* 读写数据库（chats / turns / turn2element）
* 检索 MinerU elements
* 调用 VLM 模型进行图像理解
* 保存 turn到element 的映射
* 构造上下文（caption、附近文本）

---

# 2. **系统模块总览**

下图是模块级别的分类（不含代码）：

```
                ┌────────────────────────┐
                │        用户输入         │
                └────────────┬───────────┘
                             ▼
                ┌────────────────────────┐
                │     历史对话加载(Python) │
                └────────────┬───────────┘
                             ▼
                ┌────────────────────────┐
                │    记忆摘要模块(DSPy)   │
                └────────────┬───────────┘
                             ▼
                ┌───────────────────────────┐
                │   检索判别模块(DSPy)       │
                └───────┬───────────┬───────┘
                        │           │
                 need_retrieve?-Y-->│elem_types
                        N           │
         ┌──────────────┘           ▼
         │                ┌────────────────────────┐
         │                │    问句重写(DSPy)       │
         │                └────────────┬───────────┘
         │                             ▼
         │                ┌────────────────────────┐
         │                │  元素检索(Python, DB)   │
         │                └──────┬────────┬────────┘
         │                       │        │
         │               text_elems   image_elems
         │                       │        │
         │                       │        ▼
         │                       │   图像子题生成(DSPy)
         │                       │        │
         │                       │   调用VLM(Python)
         │                       │        │→ image_evidences
         │                       ▼
         └──────────────→┌────────────────────────┐
                          │  回答生成模块(DSPy)     │
                          └────────────┬───────────┘
                                       ▼
                          ┌────────────────────────┐
                          │ 持久化与Element映射(Python) │
                          └────────────────────────┘
```

---

# 3. **各模块说明（定性描述）**

## **3.1 历史对话加载（Python）**

从 DB 中读取：

* 当前 chat_id 下所有 turn
* 或者最近 N 轮（根据系统策略）
* 拼成历史文本串 `history_text`

> 纯存取，走 Python，不需要 DSPy。

---

## **3.2 记忆摘要模块（DSPy）**

输入：`history_text`
输出：`memory_summary`（对话的压缩表示）

作用：

* 当对话很长时，提供可控大小的上下文
* 避免每轮都传入全部对话

形式（伪代码）：

```
memory_summary = Summarizer(history_text)
```

---

## **3.3 检索判别模块（DSPy）**

输入：

* `question`
* `memory_summary`

输出：

* `need_retrieve: bool`
* `elem_types: list[str]`（例如：["text","header","figure"]）

作用：
确定当前问答是否需要 RAG，是否要检索图像。

伪逻辑：

```
need_retrieve, elem_types = RetrievalDecider(question, memory_summary)
```

如果 `need_retrieve=False` → 跳过检索流程。

---

## **3.4 问句重写模块（DSPy）**

输入：

* `question`
* `memory_summary`

输出：

* `search_query`（适合数据库向量检索的 query）

用途：

* 让检索更精准
* 合并上下文信息
* 可以被 DSPy 自动调优

伪逻辑：

```
search_query = QueryRewriter(question, memory_summary)
```

---

## **3.5 元素检索（Python）**

根据：

* rewritten query
* elem_types
* 当前 collection_id / doc_ids

从 DB / vector index 检查：

* `text_elems`
* `image_elems`

伪逻辑：

```
text_elems, image_elems = search_elements(search_query, elem_types)
```

这里包括：

* 根据 elem_type 过滤
* TopK
* 数据库 join
* 映射 element_id

> 全部属于工程逻辑，不用 DSPy。

---

## **3.6 图像子问题生成（DSPy）**

对每个 `image_elem`, 构造它的 `local_context`（Python 拼接）：

* caption
* 附近文本
* 与当前 question 的关系

然后 DSPy 模块生成一个适合发送给 VLM 的“子问题”：

```
image_question = ImageQuestionGenerator(question, memory_summary, local_context)
```

> 这是纯文本逻辑 → 用 DSPy。

---

## **3.7 调用 VLM（Python）**

输入：

* `image_base64`
* `image_question`

输出：

* `image_note`（对图片的纯文本理解）

```
image_note = call_vlm(image_base64, image_question)
```

> VLM 是外部接口，不适合通过 DSPy；
> DSPy 不处理图像，因此这里必须用 Python。

---

## **3.8 最终回答生成模块（DSPy）**

输入：

* `question`
* `memory_summary`
* `text_evidences`（列表）
* `image_evidences`（列表）

输出：

* `answer_text`（自然语言答案）
* 可能依照规范输出所引用的 element_id（可选）

```
answer_text = AnswerComposer(question, memory_summary,
                             text_evidences, image_evidences)
```

作用：

* 融合所有信息
* 生成完整回答
* 按你的规定输出答案结构（如 answer + element_id 引用）

---

## **3.9 持久化相关（Python）**

包括：

* 写 turn 表
* 写 turn2element 表
* 存储 answer

伪逻辑：

```
save_turn_and_element(chat_id, question, answer_text,
                        text_elems, image_elems)
```

> 这是数据库操作，不适合 DSPy。

---

# 4. **整体控制流（伪代码）**

下面是简化版的顶层 pipeline 伪代码（无细节）：

```python
def multimodal_rag_pipeline(question, chat_id):

    # 1. 载入历史对话
    history_text = load_history(chat_id)     # Python

    # 2. 记忆摘要（DSPy）
    memory = Summarizer(history_text)

    # 3. 判别是否需要检索（DSPy）
    need_retrieve, elem_types = RetrievalDecider(question, memory)

    text_elems = []
    image_elems = []
    image_evidences = []

    if need_retrieve:
        # 4. 重写检索问句（DSPy）
        search_query = QueryRewriter(question, memory)

        # 5. 检索文本/图像元素（Python）
        text_elems, image_elems = search_elements(search_query, elem_types)

        # 6. 对每张图片 todo：这里应该改成可选的VLM理解，如果不需要的话直接用caption作为image_evidences即可。
        for img in image_elems:
            image_caption_ctx = get_image_caption(img)   # Python
            img_q = ImageQuestionGenerator(question, memory, image_caption_ctx)  # DSPy
            img_note = call_vlm(img.image_base64, img_q)                 # Python
            image_evidences.append(img_note)

    # 7. 最终回答生成（DSPy）
    answer_text = AnswerComposer(question, memory,
                                 [e.text for e in text_elems],
                                 image_evidences)

    # 8. 持久化记录（Python）
    save_turn_and_element(chat_id, question, answer_text,
                           text_elems, image_elems)

    return answer_text
```

---

# 5. **模块边界总结（最重要的三句话）**

## **（1）所有“文本 → 文本”的智能判断、重写、决策、合成 → DSPy 模块。**

包括：

* 对话摘要
* 是否检索
* 问句重写
* 给图片造子问题
* 最终回答

## **（2）所有涉及 I/O、DB、向量检索、VLM 接口 → 普通 Python 函数。**

包括：

* load history
* search elements
* 调 VLM
* 构造 local context
* 存 turn2element

## **（3）DSPy 只消费 Python 的结果，不与图片或数据库直接交互。**

---

# 6. **你可以直接交给 coder 的话**

> 「这个文档就是完整的模块交互说明。Coder 只需要把图画出来，然后按此边界实现：
> 1）所有 LLM 逻辑封装为 DSPy 模块，输入输出是纯文本；
> 2）所有 DB、检索、VLM、存储相关全部 Python；
> 3）顶层 pipeline 负责串联，不含复杂逻辑。」

