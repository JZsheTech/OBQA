from sqlalchemy import text
from ob_vector_utils import engine_conn


def demo5_1_fulltext_search_with_score(topk=3):
    with engine_conn() as conn:
        print("[Demo5] 单独的全文检索（带相似度得分） - 表: articles_demo5")

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

        # 3. 插入示例数据
        conn.execute(text("""
            INSERT INTO articles_demo5 (title, body)
            VALUES
                ('OceanBase tutorial', 'Learn how to use OceanBase database fulltext search.'),
                ('AI tutorial', 'This tutorial covers AI, database and ML basics.'),
                ('Database internals', 'Detailed analysis of distributed databases and storage systems.'),
                ('Distributed systems', 'Modern distributed database architectures overview.'),
                ('Machine Learning', 'ML and AI applied to database optimization.');
        """))

        # 4. 全文检索（单字段）
        sql_single = text("""
            SELECT 
                id, title, body,
                MATCH(body) AGAINST(:query IN NATURAL LANGUAGE MODE) AS score
            FROM articles_demo5
            WHERE MATCH(body) AGAINST(:query IN NATURAL LANGUAGE MODE)
            ORDER BY score DESC
            LIMIT :topk
        """)
        res_single = conn.execute(sql_single, {"query": "distributed", "topk": topk}).fetchall()

        print("\n🔍 [单字段检索结果 + 相似度得分]")
        for row in res_single:
            print(f"✅ id={row.id}, title='{row.title}', score={row.score:.4f}")

        # 5. 全文检索（多字段）
        sql_multi = text("""
            SELECT 
                id, title, body,
                MATCH(title, body) AGAINST(:query IN NATURAL LANGUAGE MODE) AS score
            FROM articles_demo5
            WHERE MATCH(title, body) AGAINST(:query IN NATURAL LANGUAGE MODE)
            ORDER BY score DESC
            LIMIT :topk
        """)
        res_multi = conn.execute(sql_multi, {"query": "database", "topk": topk}).fetchall()

        print("\n🔍 [多字段检索结果 + 相似度得分]")
        for row in res_multi:
            print(f"✅ id={row.id}, title='{row.title}', score={row.score:.4f}")

        # 可选：清理表
        conn.execute(text("DROP TABLE IF EXISTS articles_demo5"))


if __name__ == "__main__":
    demo5_1_fulltext_search_with_score(topk=3)
