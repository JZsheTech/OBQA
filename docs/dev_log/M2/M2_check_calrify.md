
## 集成与运行方式

- MinerU 集成模式: api调用，接口形式见docs/dev_log/M2/ref_code/parse_pdf_mineru_parallel.py，其端口已经写在默认的url中，现在已经处于可用状态，请同时在顶层环境变量配置文件中给出这个url作为可配置参数，并给出默认值注释

- 返回结构与`dependency/minerUparseDemo/parse_pdf_minerU.py` 中的一致，也可以考虑复用docs/dev_log/M2/ref_code/parse_pdf_mineru_parallel.py； ，`md_text` 稳定可用，`content_list` 的字段命名固定，需要把下面3个变量都设置为True:
    return_md: bool = True,
    return_images: bool = False,
    return_content_list: bool = False,

- 对上传处理全程“同步阻塞”，超时时直接报错终止。(默认的超时时长可以设置得久一些)

## 存储与数据模型
- 上传 PDF 的落盘目录与命名策略：你在环境变量配置文件EviQAsys/backend/app/env_setting.py中给出默认的相关配置，搞一个`UPLOAD_DIR`作为根目录，之后根据`collection_id/` 分层存储，需要基于`collection_id + filename + 文件哈希` 这个三元组做一下上传文件的去重操作

- documents 表全文存储补充:我已经修改了Data_Model的对应表schema，现在该表也会存储md的全文。
| `md_text`         | TEXT     | the markdown full text of the paper 

- `elements` 表中以下字段的类型定义：`text_content`（TEXT 无长度上限）、`image_base64`（不允许空）、`bbox_json`（JSON），枚举类型都用VARCHAR + CHECK来等效替代。

- 需要额外在 `documents` 记录中维护 `element_count` 与 `created_at` (我已经修改了对应的Data_Model)

## 处理规则与边界

- 见docs/dev_log/M2/M2_minerU_require.md

## 性能与批量处理要求

- 简单起见默认逐个文档入库。(批量只是简单地加一个循环)
- 需要事务包裹单文档的全部 elements（出错则整单回滚）
- 简单起见不设置单个 PDF 的最大体积与最大页数。

## 前端最小需求

- 前端仅需：上传 + 文档列表 两个最小视图，文档列表需要展示下面的字段（name/size/created_at/element_count/parse_status）。
- 暂不实现“查看 PDF 原文”和“高亮跳转”（按路线图应在 M5）？

## 兼容与版本

- 以当前版本的docs/en/Data_Model.md为准
- 由于documents表增加了几个字段(md_text和)，需要修改EviQAsys/backend/tests/repositories/check_documents_repo.py涉及到的相关操作(CURD和建立表格的schema)。
- M1阶段已经为docs/en/Data_Model.md中的所有表格提供了CRUD接口，在EviQAsys/backend/app/repositories中，其中针对documents和collections的接口已经经过了人工测试(在EviQAsys/backend/tests/repositories中)
- 最终测试脚本的验收口径：是否以“能上传2个 PDF 并在文档列表看到记录，DB 中有相应 elements 行”为准


