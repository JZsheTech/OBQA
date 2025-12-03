# M10 QA LLM 拆分与 AnswerAgent 调整计划 v2

## 背景与现状
- 当前 `LLMSettings` 仅持有一个 `model`，默认值是 `x-ai/grok-4-fast`，被 DSPy（query rewrite/memory 等）和 AnswerAgent 共享。
- AnswerAgent 在 `qa_orchestrator.py` 内通过 `self._llm_settings.model` 创建唯一的 OpenAI 客户端；即便 `use_image=false` 也会沿用同一模型和「多模态」提示词，user prompt 中包含空的 IMAGE ELEMENTS 描述。
- 旧的 `VisionVQASettings` 与 `VisionVQAClient` 已移除（历史文档保留备查），当前多模态仅走 AnswerAgent。
- 需求：`text_llm=x-ai/grok-4.1-fast:free`，`vision_llm=x-ai/grok-4-fast`；只有 `use_image=true` 的 AnswerAgent 调用才用 vision_llm，其余路径（DSPy 组件与 text-only AnswerAgent）全部用 text_llm，且 text-only 需要替换去掉图片描述的提示词。

## 目标
1) 明确区分 text_llm 与 vision_llm 配置，默认值分别落到 `x-ai/grok-4.1-fast:free` 与 `x-ai/grok-4-fast`。  
2) AnswerAgent 运行时根据 `use_image` 选择模型与提示词：多模态版仅在传入图片时启用，否则使用文本版提示。  
3) 其他 LLM 依赖（DSPy QueryRewriter/Memory 等）只走 text_llm。  
4) 存储与日志能反映本轮实际使用的模型，便于审计与回溯。  
5) 文档/提示词同步更新，避免继续引用图片相关描述的文本场景。

## 改造方案与任务拆解
1) 配置层拆分  
   - 在 `env_setting.py` 增加独立的 text_llm / vision_llm 默认值，引入 `DEFAULT_VISION_LLM_MODEL`（无旧 VQA 依赖）。  
   - `LLMSettings` 保持文本模型（或改为 `TextLLMSettings`），新增 `VisionLLMSettings`（可复用 `VisionVQASettings` 结构但默认绑定 vision_llm）。  
   - 衔接环境变量：`LLM_MODEL_NAME` 默认改为 `x-ai/grok-4.1-fast:free`；新增/对齐 `VISION_LLM_MODEL`（默认 `x-ai/grok-4-fast`），并保留向后兼容读取旧变量。  
   - 输出到 `__all__`，确保外层可导入。

2) DSPy/文本链路归一到 text_llm  
   - `services/llm/programs.py` 的 `DSPyPredictorFactory` 仅注入 text_llm 配置（model/api_base/key/温度/输出长度），防止无图场景误用 vision 模型。  
   - QAOrchestrator 初始化时传入 text_llm 设置给 MemoryAgent/QueryRewriter/TextRetrieveAgent 等依赖。

3) AnswerAgent 双模型支持与提示词拆分  
   - 构造阶段同时持有 text_llm_client 与 vision_llm_client；`answer()` 根据 `use_image` 分支选择客户端与模型名。  
   - 保留现有多模态 system+user 模板作为「vision 版」，仅在 `use_image=true` 且存在 image_elements 时使用；图像 block 仍按 ImageIndex 顺序附带。  
   - 新增「text-only」system/user 模板：去掉所有 IMAGE ELEMENTS 相关描述与规则，仅强调引用 `[Elem#id]`、不足时说明、避免幻想。  
   - `_build_user_prompt` 允许按模式生成（文本/多模态），禁用图片时不再输出空的 IMAGE 章节。  
   - `_generate`/日志需记录实际使用的模型名，异常 fallback 保持不变。

4) QAOrchestrator 对接与落库字段  
   - 初始化时传入 text_llm_settings + vision_llm_settings 给 AnswerAgent；`run()` 内根据 `config.use_image` 调用，`used_llm_model` 字段写入本轮实际模型（text 或 vision）。  
   - 若 `use_image=false` 但外部仍传入 `image_elements`，强制忽略图像并走文本 prompt。  
   - 评估是否需要把 `config.use_image` 透传到前端/响应中以便排查。

5) 提示词与文档同步  
   - 在 `docs/zh/工程细节/M10/` 下新增/更新多模态与文本版 AnswerAgent 提示词文档，注明使用场景与 message 组织。  
   - 更新 `README`/`docs/dev_log/M10/v1` 中涉及默认模型的描述，避免误导。  
   - 若有前端依赖的提示词片段（例如静态展示），同步替换文本版内容。

6) 手动验证计划（遵循仓库测试规范，不用 pytest）  
   - 编写独立脚本 `tests/manual/test_answer_agent_llm_switch.py`：  
     - 场景 A：`use_image=false`，提供文本元素；打印所用模型、系统/用户 prompt 片段、返回答案与 `[Elem#]`。  
     - 场景 B：`use_image=true` 且包含图像 base64；确认 messages 中包含 image_url，模型为 vision_llm，返回引用合规。  
     - 场景 C：`use_image=true` 但缺少 image_base64 时回退行为（是否仍用 vision 客户端或降级文本需在实现时明确，并打印日志）。  
   - 运行时使用 `sample_data` 的真实解析结果或现有库数据，打印日志供人工核查。

7) 风险与回滚点  
   - 默认模型切换为 `x-ai/grok-4.1-fast:free` 可能需更新线上配置/额度，需上线前确认。  
   - AnswerAgent 双客户端初始化需关注超时/headers 差异；可通过配置开关快速回退到单模型（保留旧配置读取路径）。  
   - 提示词拆分后需确保输出格式一致（citation 规则不变），避免前端解析受影响。
