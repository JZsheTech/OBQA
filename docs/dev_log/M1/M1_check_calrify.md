
# M1 矛盾点与不明确项明确

## API 协议与响应封装（Envelope）

- **封装格式不一致**：按照M1 文档示例的 `{"code":"OK","data":...}` 来，修改`docs/en/backend_frontend_interactive_design.md` 中不一致的地方。
    
- **接口范围**：DoD计划中额外包含了 `POST/DELETE` 的桩接口，将该接口推迟到 M5。
    

---

## Schema DDL 策略

- **幂等性 vs 安全性**：`schema.sql` 只做增量（使用 `CREATE IF NOT EXISTS`），如果创建已经存在的collection，给出warning，并且不允许自动覆盖之前的collection信息。只有用户明确用delete相关接口时才能做破坏性操作。
    
- **数据库创建机制**：在 Python 初始化器中读取环境变量并执行 `CREATE DATABASE IF NOT EXISTS <db>; USE <db>;`）。
    
- **向量维度**：数据模型中emb_dim维度由环境变量决定，后续用f"VECTOR{emb_dim}"字符串来构建SQL字符串，通过环境变量 `VECTOR_DIM` 配置。
    
- **级联规则**：`docs/en/Data_Model.md` 外键的级联行为就是级联删除。（如 `documents.collection_id`、`elements.doc_id`、`turns.chat_id`、`turn2evidence.*`）使用 `ON DELETE CASCADE` 策略。
    
- **ENUM 换成VARCHAR**：`elements.elem_type` 定义为 `ENUM('text','header','image','table','equation')`。数据库实际实现时改用 `VARCHAR` + `CHECK` 以保持兼容。
    
- **时间戳字段**：统一使用 `DEFAULT CURRENT_TIMESTAMP`，表中元组(行)只需要`created_at` 信息，不需要`updated_at`。
    

---

## 迁移触发与启动行为

- **双迁移路径问题**：系统启动时创建或者加载数据库表，由python程序sdk去执行SQL语句，不要让用户手动去运行 `schema.sql` 。
    
- **失败语义**：若启动时 OceanBase 不可用，API 应该立即失败、跳过迁移，并给出错误信息。
    

---

## Repository 层与命名一致性

- **文件命名不一致**：统一按照 M1 文档的 `turn2evidence_repo.py` 命名，修改Roadmap 中的 `t2e_repo.py`文件命名 。
    
- **包导出策略**：在 `EviQAsys/backend/app/repositories/__init__.py` 中重新导出各 Repository 类，并在业务层统一导入路径。
    
- **SQL 辅助函数**：M1要提供 `dict_to_insert` 等辅助函数。必须完全保持原生 SQL（不引入 ORM），以及统一的最小辅助函数集合。
    

---

## 数据库连接与配置

- **文件位置**：计划将数据库连接助手放在 `repositories/db.py`，但模板中也有 `services/db_access/`。选择 `repositories/db.py` ， 另一个请删掉。
    
- **DSN 与字符集**：数据库中统一使用 `charset=utf8mb4` 进行连接。
    
- **环境变量约定**：确定最终环境变量名及默认值（如 `OB_HOST/OB_PORT/OB_USER/OB_PASSWORD/OB_DEFAULT_DATABASE/DATABASE_CONNECT_TIMEOUT`、`VECTOR_DIM`）。允许代码创建数据库，应使用默认的环境变量创建。
	- 需要搞一个统一的env_setting.py文件来设置这些环境变量，后续其他环境变量的命名你可以自己决定，注意保证良好的可读性并且统一注册到env_setting.py文件中即可。

---

## 数据访问语义

- **事务与自动提交**：通过 SQLAlchemy 执行 DDL + 多语句脚本时，暂时依赖驱动层自动提交，先不考虑事务性。
    
- **行映射格式**：Repository 将返回字典形式的结果，你保证字典中的key和数据库中的字段名一致就行，并且在代码中根据数据库中的字段类型为对应的key加上注释。
    

---

## 文档间对齐

- **索引定义一致性**：M1 引用 `idx_chat_turn`、`idx_turn_element`（桥接表），这些索引其实只和性能有关，不影响系统初期能否跑通，所以可以暂时先不建立，相关标量索引和向量索引的建立语句可以全部留空，并在文档中删掉。因为检索时并不依赖这些索引。
    
- **统一模式原则**：所有 collection 共享全局表。 M1 的脚手架中不能包含按 collection 创建独立表的逻辑。
    

---

## 验证范围（人工测试）

- **运行环境**：开发者保证依赖环境全部配置好了。
    
- **测试数据清理**：需明确人工测试是否负责自行清理插入的数据，迁移脚本不得删除已有数据。
    

---

## FastAPI 层面（M1 阶段）

- **路由结构**：需确认挂载路径（统一加 `/api` 前缀），CORS 策略的基础设置你按照简单可用的方式自行决定(我不懂这个)。
    
- **空状态响应**：`GET /collections` 应返回空列表 `[]`，且封装在统一响应格式中。留待后续阶段根据加载到的字典补充。
    
