from sqlalchemy import   text
import random
from sqlalchemy import func, text

from ob_vector_utils import (
    OB_DEMO_TABLE,
    ensure_pyobvector_client,
    engine_conn,
    drop_demo_table,
    create_demo_table,
)

def demo5_fulltext_search():

    with engine_conn() as conn:
        print("[Demo5] 单独的全文检索 - 表: articles_demo5")

        # 1. 删除旧表
        conn.execute(text("DROP TABLE IF EXISTS articles_demo5"))

        # 2. 创建表并建立全文索引
        conn.execute(text("""
            CREATE TABLE articles_demo5 (
                id INT PRIMARY KEY AUTO_INCREMENT,
                title VARCHAR(255),
                body TEXT,
                FULLTEXT INDEX idx_title_body(title, body),
                FULLTEXT INDEX idx_body(body)          
            )
        """))

        # 3. 插入数据
        conn.execute(text("""
            INSERT INTO articles_demo5 (title, body)
            VALUES
                ('OceanBase tutorial', 'Learn how to use OceanBase database fulltext search.'),
                ('AI tutorial', 'This tutorial covers AI 、 database and ML basics.'),
                ('Database internals', 'Detailed analysis of distributed databases.');
        """))

        # 4. 全文检索
        sql = text("""
            SELECT id, title, body
            FROM articles_demo5
            WHERE MATCH(body) AGAINST(:query IN NATURAL LANGUAGE MODE)
        """)
        res = conn.execute(sql, {"query": "distributed"}).fetchall()

        print("🔍 单字段检索结果：")
        for row in res:
            print(row)

        # 同时检索多个字段
        sql_multi = text("""
            SELECT id, title, body
            FROM articles_demo5
            WHERE MATCH(title, body) AGAINST(:query IN NATURAL LANGUAGE MODE)
        """)
        res_multi = conn.execute(sql_multi, {"query": "database"}).fetchall()   

        print("🔍 多字段检索结果：")
        for row in res_multi:
            print(row)

        conn.execute(text("DROP TABLE IF EXISTS articles_demo5"))

demo5_fulltext_search()
