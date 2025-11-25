import json
from sqlalchemy import text
from ob_vector_utils import engine_conn

# 注意：当前混合检索的api不支持投影操作，也就是返回的row里面包含表中的所有属性的值,需要手动做投影操作。
# 混合检索时 knn的topK只是其中一部分，还有full-text那边的结果也会一起加进来，所以总的结果数可能会超过topK
        # row = conn.execute(sql, {"parm": json_str}).fetchone()
        # print(row[0], "\n") # row[0]中包含了所有结果，格式是 list[dict]
# 示例的输出格式:
"""

[
  {
    "c1": 3,
    "query": "hello world, how are you",
    "_score": 0.7006369426751594,
    "vector": "[1,1,1]",
    "content": "oceanbase oracle database",
    "test_id": 14
  },
  {
    "c1": 6,
    "query": "hello world, where are you from",
    "_score": 0.7006369426751594,
    "vector": "[2,1,1]",
    "content": "starrocks oceanbase database",
    "test_id": 17
  }
] 
"""

# ================================
# 1. 初始化表结构 + 插入数据
# ================================
def setup_doc_table():
    print("=== 初始化测试表 doc_table ===")

    create_table_sql = text("""
        DROP TABLE IF EXISTS doc_table;

        CREATE TABLE doc_table(
            c1 INT,
            test_id INT,
            vector VECTOR(3),
            query VARCHAR(255),
            content VARCHAR(255),
            VECTOR INDEX idx1(vector) WITH (distance=l2, type=hnsw, lib=vsag),
            FULLTEXT INDEX idx2(query),
            FULLTEXT INDEX idx3(content)
        );
    """)

    insert_sql = text("""
        INSERT INTO doc_table VALUES
            (1, 12, '[1,2,3]', "hello world", "oceanbase Elasticsearch database"),
            (2, 13, '[1,2,1]', "hello world, what is your name", "oceanbase mysql database"),
            (3, 14, '[1,1,1]', "hello world, how are you", "oceanbase oracle database"),
            (4, 15, '[1,3,1]', "real world, where are you from", "postgres oracle database"),
            (5, 16, '[1,3,2]', "real world, how old are you", "redis oracle database"),
            (6, 17, '[2,1,1]', "hello world, where are you from", "starrocks oceanbase database");
    """)

    with engine_conn() as conn:
        conn.execute(create_table_sql)
        conn.execute(insert_sql)

    print("=== doc_table 初始化完成 ===\n")

def hybrid_search_method2_with_boost():
    print("=== 混合检索（带 boost）- 方法2：绑定 JSON 字符串参数 ===")

    param_dict = {
        "query": {
            "query_string": {
                "fields": ["query", "content"],
                "query": "hello oceanbase",
                "boost": 2.0      # 提高全文检索权重
            }
        },
        "knn": {
            "field": "vector",
            "k": 1,
            "query_vector": [1, 2, 3],
            "boost": 1.0        # 向量检索权重
        }
    }

    # 方法2 —— 将 dict 转成 JSON 字符串，然后作为 SQL 参数绑定
    json_str = json.dumps(param_dict)

    sql = text("""
        SELECT JSON_PRETTY(DBMS_HYBRID_SEARCH.SEARCH(
            'doc_table',
            :parm
        ));
    """)

    with engine_conn() as conn:
        row = conn.execute(sql, {"parm": json_str}).fetchone()
        print(row[0], "\n") # row[0]中包含了所有结果，格式是 list[dict]


# ================================
# 2. 混合搜索 - 方法2（json.dumps 参数绑定）
# ================================
def hybrid_search_method2_no_boost():
    print("=== 混合检索（无 boost）- 方法2：绑定 JSON 字符串参数 ===")

    param_dict = {
        "query": {
            "query_string": {
                "fields": ["query", "content"],
                "query": "hello oceanbase"
            }
        },
        "knn": {
            "field": "vector",
            "k": 5,
            "query_vector": [1, 2, 3]
        }
    }

    json_str = json.dumps(param_dict)

    sql = text("""
        SELECT JSON_PRETTY(DBMS_HYBRID_SEARCH.SEARCH(
            'doc_table',
            :parm
        ));
    """)

    with engine_conn() as conn:
        row = conn.execute(sql, {"parm": json_str}).fetchone()
        print(row[0], "\n")


# ================================
# 3. 混合搜索 - 方法3（SQL literal）
# ================================
def hybrid_search_method3_with_boost():
    print("=== 混合检索（带 boost）- 方法3：SQL literal 拼接 ===")

    param_dict = {
        "query": {
            "query_string": {
                "fields": ["query", "content"],
                "query": "hello oceanbase",
                "boost": 2.0
            }
        },
        "knn": {
            "field": "vector",
            "k": 5,
            "query_vector": [1, 2, 3],
            "boost": 1.0
        }
    }

    json_literal = json.dumps(param_dict).replace("'", "\\'")

    sql = text(f"""
        SELECT JSON_PRETTY(DBMS_HYBRID_SEARCH.SEARCH(
            'doc_table',
            '{json_literal}'
        ));
    """)

    with engine_conn() as conn:
        row = conn.execute(sql).fetchone()
        print(row[0], "\n")


# ================================
# 4. MAIN
# ================================
if __name__ == "__main__":
    setup_doc_table()
    # hybrid_search_method2_no_boost()
    hybrid_search_method2_with_boost()
    # hybrid_search_method3_with_boost()
