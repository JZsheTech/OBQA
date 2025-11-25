import json
from sqlalchemy import text
from ob_vector_utils import engine_conn


def setup_test_table():
    """创建测试表并插入数据。"""
    print("=== 初始化测试表 doc_table ===")
    with engine_conn() as conn:

        conn.execute(text("DROP TABLE IF EXISTS doc_table"))

        conn.execute(text("""
            CREATE TABLE doc_table(
                c1 INT,
                vector VECTOR(3),
                query VARCHAR(255),
                content VARCHAR(255),
                VECTOR INDEX idx1(vector) WITH (distance=l2, type=hnsw, lib=vsag),
                FULLTEXT INDEX idx2(query),
                FULLTEXT INDEX idx3(content)
            );
        """))

        insert_sql = text("""
            INSERT INTO doc_table VALUES
            (1, '[1,2,3]', "hello world", "oceanbase Elasticsearch database"),
            (2, '[1,2,1]', "hello world, what is your name", "oceanbase mysql database"),
            (3, '[1,1,1]', "hello world, how are you", "oceanbase oracle database"),
            (4, '[1,3,1]', "real world, where are you from", "postgres oracle database"),
            (5, '[1,3,2]', "real world, how old are you", "redis oracle database"),
            (6, '[2,1,1]', "hello world, where are you from", "starrocks oceanbase database");
        """)

        conn.execute(insert_sql)

    print("=== doc_table 初始化完成 ===\n")


def test_pass_json_as_param():
    """
    测试是否可以通过 SQL 参数绑定方式，将 JSON 作为 DBMS_HYBRID_SEARCH.SEARCH 的第二个参数传递。
    """
    param_dict = {
        "knn": {
            "field": "vector",
            "k": 3,
            "query_vector": [1, 2, 3]
        }
    }

    # Test 1: Python dict (必然失败)
    print("=== 测试 #1：直接传 Python dict（预期失败）===")
    try:
        with engine_conn() as conn:
            result = conn.execute(
                text("SELECT DBMS_HYBRID_SEARCH.SEARCH('doc_table', :parm)"),
                {"parm": param_dict},
            ).fetchone()
        print("SUCCESS:", result)
    except Exception as e:
        print("ERROR:", e)

    # Test 2: json.dumps 字符串（DBMS_HYBRID_SEARCH 解析失败）
    print("\n=== 测试 #2：使用 json.dumps 后作为参数（预期 SEEKDB 解析失败）===")
    try:
        json_str = json.dumps(param_dict)
        with engine_conn() as conn:
            result = conn.execute(
                text("SELECT DBMS_HYBRID_SEARCH.SEARCH('doc_table', :parm)"),
                {"parm": json_str},
            ).fetchone()
        print("SUCCESS:", result)
    except Exception as e:
        print("ERROR:", e)

    # Test 3: 直接拼 SQL literal（唯一成功方式）
    print("\n=== 测试 #3：拼 SQL literal（预期唯一成功方式）===")
    try:
        json_literal = json.dumps(param_dict).replace("'", "\\'")
        sql = text(f"""
            SELECT JSON_PRETTY(DBMS_HYBRID_SEARCH.SEARCH(
                'doc_table',
                '{json_literal}'
            ));
        """)
        with engine_conn() as conn:
            result = conn.execute(sql).fetchone()
        print("SUCCESS:\n", result[0])
    except Exception as e:
        print("ERROR:", e)


if __name__ == "__main__":
    setup_test_table()
    test_pass_json_as_param()
