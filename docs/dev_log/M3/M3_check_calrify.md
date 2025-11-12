对问题清单的回答如下：
## 嵌入服务与模型
- embedding-api相关的使用全部参考 dependency/multiModalEmbedding/demo_jina_local_embedding.py(无需身份验证，api_key随便填)和dependency/multiModalEmbedding/demo_jina_api_embedding.py(需要提供有效的api_key)， 需要留出一些可配置参数在2者之间切换。
- `jinaembeddingv4` 实际输出维度是2048，但是要留成1个可配置的参数

## 多模态策略与元素范围
- 参与嵌入的纯文本元素类型包括text, header， 对2者进行统一处理
- 对 `image/table/equation`：默认“文本+图片联合嵌入”， 图片缺失时退化为文本-only
- 文本来源：对图片/表格，使用 `text_caption` + `text_content` 参与联合嵌入？

## OceanBase 与相似度计算
- 语义相似度检索参考dependency/oceanBaseDemo/demo3_scalar_filter_vector_exact.py
- 全文检索参考dependency/oceanBaseDemo/demo6_fulltext_search_with_scalar.py 和 dependency/oceanBaseDemo/demo5_1_fulltext_search_topK_score.py
- 默认用topK进行检索，不人为设定相似度阈值

## 检索接口需求 
返回的信息按照相关性分数从大到小的顺序排列，需要包括score.

- 对指定的collection_id中的所有文档中的elements进行语义相似度检索，返回topK的elements的信息
- 对指定的document_id对应的文档中的elements进行语义相似度检索，返回topK的elements的信息

- 对指定的collection_id中的所有文档中指定类型的elements进行语义相似度检索(比如只对text类型的元素进行检索)，返回topK的elements的信息
- 对指定的document_id对应的文档中指定类型的elements进行语义相似度检索(比如只对text类型的元素进行检索)，返回topK的elements的信息

- 对指定的collection_id中的所有文档中的elements进行全文检索，返回topK的elements的信息
- 对指定的document_id对应的文档中的elements进行全文检索，返回topK的elements的信息

- 对指定的collection_id中的所有文档中指定类型的elements进行全文检索(比如只对text类型的元素进行检索)，返回topK的elements的信息
- 对指定的document_id对应的文档中指定类型的elements进行全文检索(比如只对text类型的元素进行检索)，返回topK的elements的信息

- 对指定的collection_id中的所有文档进行全文检索，返回topK相关的文档的信息

## 触发方式与批处理
M3 期望的最小触发路径是后端脚本优先，不需要提供对前端的 API 触发，因为向量检索操作发生在后端，后端会把检索到的内容喂给LLM生成答案，前端只要接收这个答案就行，不需要直接通过检索得到相关信息。
批处理参数：按照建议的来
失败策略：单条失败直接让整个程序都退出

## 资源与运维
环境部署已经全部到位, 资源默认没有限制
需要在EviQAsys/backend/app/env_setting.py中配置embedding相关的环境变量，并给出默认值设置。

## 其它
- 需要在 M3 暂时跳过“去重与类型分桶”的复杂逻辑，仅保留接口预留点？
- 前端不需要在 M3 提供最小的调试视图，只要后端功能测试完成即可。
