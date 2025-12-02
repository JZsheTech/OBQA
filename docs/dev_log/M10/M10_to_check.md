# M10 待确认/待决策事项

1. 参数默认值与前端输入范围（@todo[1]）
   - text_retrieve_topk、image_retrieve_topk、text_memory_topk、image_memory_topk、use_image、use_page_in_text_retrieve、page_retrieve_topk、text_search_mode 的默认值与允许范围/步进未定；需决定后端默认值以及前端控件的最小/最大值和步长。
   text_retrieve_topk = 8, image_retrieve_topk = 2, text_memory_topk = 4,  image_memory_topk = 1, use_page_in_text_retrieve = 0, page_retrieve_topk = 4, text_search_mode = "hybrid"
2. MEMORY_MAX_LEN 与总结策略（@todo[2]）
   见 docs/zh/工程细节/M10/MemoryAgent提示词和规则.md 文档。

3. DSPy/LLM 配置（@todo[3]）
   - 系统中Agent 的 query rewrite / summary / element 选择所用的基座LLM模型、embedding 模型复用线上已有模型，提示词可根据需要进行适当修改-除了文档中指定部分的提示词外，你可以自由发挥。(embedding就是当前的jina-embeddingv4, 问答LLM统一成VLM(也能兼容text-llm的输入)，即"x-ai/grok-4-fast"
4. AnswerAgent 提示与输入打包方式（@todo[4]）
   见文档 docs/zh/工程细节/多模态answerAgent提示词.md 中的详细描述

5. 候选去重后的排序策略（@todo[5]）
   - 去重后，对于文本类型的元素，把检索agent得到的element按相关性从大到小排列，然后再把记忆agent给出的element按给出的顺序排列，拼接在后面；图片类型的元素同理。
6. turn2element 历史数据处理（@todo[6]）
   - 删除 turn2element 后，已有数据会手动重建，不需要迁移。
7. ImageRetrieveAgent 的 rewrite/embedding 策略（@todo[7]）
   - 图片检索可复用文本的 rewrite/embedding。
8. evidence_no 在多实例/重连时的一致性（@todo[8]）
   - evidence_no 保存在单实例内存，不考虑用户对同一个session打开多个窗口的情况，后端做会话级缓存即可。
