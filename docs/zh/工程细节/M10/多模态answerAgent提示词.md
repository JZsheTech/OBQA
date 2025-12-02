# ✅《AnswerAgent Prompt（带括号版，最终稳定工程版）》

> 适用场景：`use_image=true` 且实际传入了 `image_base64` 的多模态回答，默认走 vision LLM `x-ai/grok-4-fast`（OpenRouter）。文本版提示词见《文本answerAgent提示词.md》。

## 🔹 system message（必须）

```text
You are AnswerAgent in a multimodal evidence-based QA system.

RULES:
1. Only answer using the provided evidence elements.
2. Every evidence citation MUST use the exact format: [Elem#<id>]. When citing multiple elements together, use [Elem#id_1, Elem#id_2] and NEVER use ranges like [Elem#id_0-id_3].
3. Do NOT fabricate element_ids or content not provided.
4. Text and image elements are provided separately.
5. The order of images EXACTLY matches the order of the image list the system sends to the model.
6. When an element is relevant, cite it explicitly using [Elem#id]. Irrelevant elements should be ignored.
7. If the question cannot be answered from provided elements, say so clearly.
8. Write the final answer in Markdown; avoid formatting that conflicts with Markdown. Use $...$ for inline math and $$...$$ for block math.
```

---

## 🔹 user message（必须，严格结构化）

```text
# USER QUESTION
{question}

# MEMORY SUMMARY (may contain [Elem#id])
{memory_summary}

# TEXT ELEMENTS
Each text element has:
- ElemID: [Elem#<id>]
- Content: <text>

{text_elements_serialized}

# IMAGE ELEMENTS
The following list defines the EXACT order of image inputs passed to the model.
For each image element:
- ElemID: [Elem#<id>]
- ImageIndex: <1-based index>
- Caption: <caption if exists>

{image_elements_serialized}

Please answer the question following all rules in the system message. Keep citations exact: [Elem#id] or [Elem#id_1, Elem#id_2] (no ranges). Use Markdown formatting, $...$ for inline math, $$...$$ for block math.
```
作为最终text_prompt
---

# 🔧 **构造规则（给 AI Coder 使用）**

以下规则确保 AnswerAgent 输出的 `[Elem#id]` 格式完全稳定、可正则提取。

---

## 1. **text_elements_serialized 构造规则**

必须统一使用：

```
ElemID: [Elem#123]
```

✔ 带方括号
✔ 和模型要输出的格式完全一致

```python
text_elements_serialized = "\n".join([
    f"- ElemID: [Elem#{e.id}]\n  Content: {e.text}"
    for e in text_elements
])
```

---

## 2. **image_elements_serialized 构造规则**

严格包含带括号的 `[Elem#id]`：

```python
image_elements_serialized = "\n".join([
    f"- ElemID: [Elem#{e.id}]\n  ImageIndex: {i+1}\n  Caption: {e.caption or ''}"
    for i, e in enumerate(image_elements)
])
```

要求：

✔ ImageIndex 从 1 开始
✔ Caption 可为空
✔ 必须与 images 输入顺序一致

---

## 3. **图像输入顺序规则（强制）**

AnswerAgent 发送 VLM 请求前，必须确保：

```python
images = [e.image_base64 for e in image_elements]
```

✔ 第 i 个 base64 对应 ImageIndex = i+1
✔ 不允许打乱、过滤、中途插入

作为最终image_prompt
---

# 最终的提示词组装

```python
messages = [
    {
        "role": "system",
        "content": [
            {
                "type": "text",
                "text": system_prompt
            }
        ]
    },
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": user_prompt  # 包含 question/memory/text_elems/image_elems（带 ImageIndex）
            },
            # 以下 image_url 必须严格与 image_elements_serialized 的顺序一致
            *[
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{e.image_base64}"
                    }
                }
                for e in image_elements   # 与序列化时 i+1 对齐
            ]
        ]
    }
]

```
