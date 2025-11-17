
## DSPy 编排与 LLM 集成

M4采用的整个问答Agent的编排方式请参考文档: "docs/zh/dspy问答Agent设计.md"

文本 LLM 后端：目前 `env_setting` 已有 `OLLAMA_OPENAI_BASE_URL`。约定 DSPy 统一通过该 OpenAI 兼容端点调用，并用一个环境变量（如 `QA_LLM_MODEL`）指定模型名

## Evidence 锚点与存储策略

具体的前后端锚点通信要求见文档 "docs/zh/工程细节/Evidence 渲染规范.md" 。

- `turn2element` 写入范围：只为“答案文本里真实出现的 `[Elem#id]`”写记录，而不为未被引用但参与上下文的候选元素写入.

## Chat 记忆与上下文构造

- 记忆窗口：路线图建议“仅拼接最近若干轮（例如 3 轮）”。M4 可以先实现“只取最近 N=3 轮问答作为上下文”，暂不做历史摘要；如果之前的对话轮数不足3，则有多少拼多少。拼的时候注意，凡是有[Elem#id]的引用锚点，需要额外把evidence的文本内容拼接到prompt中

## API 形态与返回结构
这个设计我也不太懂，你自由发挥即可，注意别搞得太复杂。

## 图像理解（可选路径）

M4 DoD 中的图像理解路径先作为一个 feature flag：默认仅使用 caption 参与回答，`vision_vqa_summarize` 初期可以是占位实现（始终返回空字符串）

后期正式开启图像 VQA时，VQA 摘要与 caption 拼接后的文本是只在一次回答流程中临时使用，不需要保存到数据库中。


## 失败与降级策略（锚点相关）
- 当 LLM 输出的锚点有问题（完全没有 `[Elem#id]`，或包含不在候选列表中的 `element_id`）时，预期的降级策略是什么：A）仍返回答案文本但不写 `turn2element`，前端只显示无 Evidence 的回答；(并在回答中加一个Warning: 触发了检索但没有获得有用的证据)
