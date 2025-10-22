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


def demo6_fulltext_with_filter():
    with engine_conn() as conn:
        print("[Demo6] 全文检索 + 标量过滤 - 表: articles_demo6")

        # 1. 删除旧表
        conn.execute(text("DROP TABLE IF EXISTS articles_demo6"))

        # 2. 创建表并建立全文索引
        conn.execute(text("""
            CREATE TABLE articles_demo6 (
                id INT PRIMARY KEY AUTO_INCREMENT,
                title VARCHAR(255),
                category VARCHAR(50),
                body TEXT,
                FULLTEXT INDEX idx_title_body(title, body)
            )
        """))

        # 3. 插入数据
        conn.execute(text("""
            INSERT INTO articles_demo6 (title, category, body)
            VALUES
                ('OceanBase intro', 'database', 'OceanBase database introduction tutorial'),
                ('AI tutorial', 'ai', 'Deep learning introduction tutorial'),
                ('Distributed SQL', 'database', 'Exploring distributed database systems');
        """))

        # 4. 混合检索：全文匹配 + 类别过滤
        sql = text("""
            SELECT id, title, category, body
            FROM articles_demo6
            WHERE MATCH(title, body) AGAINST(:query IN NATURAL LANGUAGE MODE)
              AND category = :category
        """)
        res = conn.execute(sql, {"query": "tutorial", "category": "database"}).fetchall()

        print("🔍 检索结果（数据库类 tutorial）：")
        for row in res:
            print(row)

demo6_fulltext_with_filter()

