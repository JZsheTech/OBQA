# 当前 enable_image_vqa=True 时的问答行为

- 触发方式：前端在 `POST /api/chats/{chat_id}/turns` 传 `enable_image_vqa=true`，或通过环境变量 `QA_ENABLE_IMAGE_VQA=1` 设为默认。`QAOrchestrator` 在 `run()` 中用 `QAFlowConfig.with_overrides` 合并请求值与 env 默认，最终 `config.enable_image_vqa` 为真时才进入视觉分支。
- 执行路径：检索阶段把 `elem_type=image` 的命中收集到 `image_candidates`（受 `image_evidence_limit` 约束，默认 4）。若启用视觉分支，会懒加载 `VisionVQAClient` 并传递给 `_build_image_evidences`。
- VQA 调用：`_build_image_evidences` 对每个图片候选用 `ImageQuestionGenerator.generate`（DSPy，有回退）生成派生问句，再调用 `VisionVQAClient.summarize(element_id, derived_question, local_context)`。`summarize` 会查库拿 `image_base64`，拼出包含 question/caption/附近上下文的 prompt，使用 OpenAI Python SDK 调用 `VISION_VQA_ENDPOINT`（默认 `https://openrouter.ai/api/v1/`）与指定 `model`（默认 `x-ai/grok-4-fast`），并从 `choices[0].message.content`/`result` 提取文本。
- 证据落地：若 VQA 返回文本，则把返回值附加为 `Vision summary: ...` 拼到原 caption/context 后形成图片 evidence；调用失败（无 image_base64、HTTP 异常或空结果）会记录 warning，图片 evidence 只保留原 caption/context 或被跳过（为空时）。
- 回答生成：图片 evidence 与文本 evidence 一并传给 `AnswerComposer`，由文本 LLM 生成最终回答并引用 `[Elem#id]`。
- 是否接入真实视觉 LLM：是。视觉路径通过 OpenAI Python SDK 直连可配置的 OpenAI 兼容多模态接口，默认指向 OpenRouter 的 `x-ai/grok-4-fast`；不存在本地伪造或占位逻辑，只是当接口未部署或元素缺少 `image_base64` 时会降级为仅用 caption/context 的文本描述，不再调用 VLM。
- 现有限制：只有检索命中图片元素时才会触发 VQA；DSPy 不可用时派生问句退化为启发式文本，但不影响真实视觉接口的调用；接口凭证/endpoint 需在环境变量中正确配置，否则会被视为调用失败。 
