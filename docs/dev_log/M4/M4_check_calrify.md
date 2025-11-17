
## DSPy 编排与 LLM 集成

DSPy 模块拆分：M4 采用“记忆模块 + 检索判别模块 + 问句重写模块 + 检索模块 + 检索结果 + (VQA模块：图像->文本回答) + 文本回答模块”的模块化 DSPy 编排

先记忆模块从数据库中获取记忆；
根据当前记忆和用户输入的Question判断是否要进行检索；
如果要检索，用问句重写模块将question改写成RAG用的query
query送给检索模块，检索模块调用RAG方法检索到相关的数据
回答模块：回答模块结合检索得到的结果拼接产生上下文(可选对图片element做一个VQA，可能要扩展一个VQA模块，考虑VQA的question要如何根据上下文生成)，给出完整的回答，并且提取回答结果中的elements存turn2elements表。

dspy的设计比较特殊，并不是什么功能都需要以模块的形式呈现，有些内容只要封装成1个函数，在dspy模块中去调用即可，或者用dspy.React让它自主决定应该调用什么方法，所以上面的模块设计可能不一定完全合理。


文本 LLM 后端：目前 `env_setting` 已有 `OLLAMA_OPENAI_BASE_URL`。约定 DSPy 统一通过该 OpenAI 兼容端点调用，并用一个环境变量（如 `QA_LLM_MODEL`）指定模型名

## Evidence 锚点与存储策略

- `turns.llm_answer_text` 的存储格式：DB 中保留原始 LLM 输出（含 `[Elem#id]`），API 在返回时临时替换为 `[Evidence#no]`

- Evidence 编号的“历史序列”来源: 按照 M4_refactor_doc 的说法，从历史 `llm_answer_text` 中用正则抽取 `[Elem#id]` 再去重。因为前端展示前正则替换这一步是无法避免的。

- `turn2element` 写入范围：只为“答案文本里真实出现的 `[Elem#id]`”写记录，而不为未被引用但参与上下文的候选元素写入.

## Chat 记忆与上下文构造

- 记忆窗口：路线图建议“仅拼接最近若干轮（例如 3 轮）”。M4 可以先实现“只取最近 N=3 轮问答作为上下文”，暂不做历史摘要；如果之前的对话轮数不足3，则有多少拼多少。拼的时候注意，凡是有[Elem#id]的引用锚点，需要额外把evidence的文本内容拼接到prompt中

## API 形态与返回结构
这个设计我也不太懂，你自由发挥即可，注意别搞得太复杂。

## 图像理解（可选路径）

M4 DoD 中的图像理解路径先作为一个 feature flag：默认仅使用 caption 参与回答，`vision_vqa_summarize` 初期可以是占位实现（始终返回空字符串）

后期开启图像 VQA，VQA 摘要与 caption 拼接后的文本要回写到 DB（存到turn2element表中），用于拼接memory时作为图片element的内容。

turn2element表要给出element的type和实际上传递给llm的text_content；对于图像element,包括VQA得到的答案以及VQA中LLM提出的问题；对于文本模态的element，就给element表里的text_content就行(主要是为了方便恢复memory)

## 失败与降级策略（锚点相关）
- 当 LLM 输出的锚点有问题（完全没有 `[Elem#id]`，或包含不在候选列表中的 `element_id`）时，预期的降级策略是什么：A）仍返回答案文本但不写 `turn2element`，前端只显示无 Evidence 的回答；(并在回答中加一个Warning: 触发了检索但没有获得有用的证据)
