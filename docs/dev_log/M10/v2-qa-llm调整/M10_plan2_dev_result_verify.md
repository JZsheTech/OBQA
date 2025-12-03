# M10 QA LLM 拆分 & AnswerAgent 双模型改造结果

## 完成内容
- 配置层拆分：`DEFAULT_TEXT_LLM_MODEL` 默认切到 `x-ai/grok-4.1-fast:free`，新增 `DEFAULT_VISION_LLM_MODEL` / `VisionLLMSettings` / `get_vision_llm_settings`，`LLMSettings` 仅代表文本链路（统一复用 API base/key/header/温度/输出长度）。`template_config.yaml` 补充了 vision 相关占位。
- DSPy 仅注入文本 LLM：`DSPyPredictorFactory` 接收 `text_llm_settings`，QAFlow 初始化时传入文本 LLM 配置给 QueryRewriter/MemoryAgent。
- AnswerAgent 双客户端：构造时同时持有文本/视觉 OpenAI 客户端；`answer()` 基于 `use_image` 与是否存在 `image_base64` 自动选择文本或多模态 prompt，并返回实际使用的 `used_model`。`use_image=true` 但缺少图片时降级为文本提示词，日志记录丢弃的图片元素。
- QAOrchestrator 衔接：初始化时注入 text+vision LLM 设置，`used_llm_model` 入库时写入本轮实际模型；use_image=false 时强制忽略传入的图片列表。日志附带 used_model 与 use_image 状态。
- 提示词/文档：新增《docs/zh/工程细节/M10/文本answerAgent提示词.md》；多模态提示词文档标注仅在 use_image=true 且传入图片时使用；README/M10 v1 计划文档同步默认模型描述。
- 手动脚本：新增 `EviQAsys/backend/tests/manual/test_answer_agent_llm_switch.py`，基于真实 elements（按 document_id 读取）覆盖场景 A 文本、B 多模态（含 base64）、C use_image=true 无 base64 的降级逻辑，打印实际模型、prompt 片段与引用的 [Elem#]。

## 验证建议
- 运行手动脚本：`python EviQAsys/backend/tests/manual/test_answer_agent_llm_switch.py --document-id <id> --question "..." --text-limit 4 --image-limit 2`，确保 doc 含真实解析数据；按输出核对模型切换、prompt 结构、answer 中的 `[Elem#]`。
- 现有 QA 流手工链路可复用 `tests/manual/test_m4_qa_flow.py` 先准备数据，再执行上方脚本观察切换效果。
- 本地 `python -m compileall ...` 未执行成功（环境缺少 `python` 命令），未做自动化校验。
