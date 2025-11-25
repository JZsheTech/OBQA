import json
from sqlalchemy import text
from ob_vector_utils import engine_conn


# ================================
# 1. 初始化表结构 + 插入数据
# ================================
def setup_doc_table():
    print("=== 初始化测试表 doc_table ===")

    create_table_sql = text("""
        DROP TABLE IF EXISTS doc_table;

        CREATE TABLE doc_table(
            c1 INT,
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
            (1, '[1,2,3]', "hello world", "oceanbase Elasticsearch database"),
            (2, '[1,2,1]', "hello world, what is your name", "oceanbase mysql database"),
            (3, '[1,1,1]', "hello world, how are you", "oceanbase oracle database"),
            (4, '[1,3,1]', "real world, where are you from", "postgres oracle database"),
            (5, '[1,3,2]', "real world, how old are you", "redis oracle database"),
            (6, '[2,1,1]', "hello world, where are you from", "starrocks oceanbase database");
    """)

    with engine_conn() as conn:
        conn.execute(create_table_sql)
        conn.execute(insert_sql)

    print("=== doc_table 初始化完成 ===\n")


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
    hybrid_search_method2_no_boost()
    hybrid_search_method3_with_boost()
