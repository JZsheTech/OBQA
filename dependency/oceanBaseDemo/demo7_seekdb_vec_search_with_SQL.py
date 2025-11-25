import json
import random
from sqlalchemy import text

from ob_vector_utils import engine_conn


TABLE_NAME = "articles_seekdb_demo7"
EMBED_DIM = 384


def _generate_embedding(seed: int, dim: int = EMBED_DIM):
    """Create a deterministic vector so the demo output is repeatable."""
    rng = random.Random(seed)
    return [round(rng.random(), 6) for _ in range(dim)]


def _seed_articles():
    return [
        {
            "id": 1,
            "title": "AI and Machine Learning",
            "content": "Artificial intelligence is transforming analytics and content generation.",
            "embedding": _generate_embedding(seed=11),
        },
        {
            "id": 2,
            "title": "Database Systems",
            "content": "Modern distributed databases provide high performance and resilient storage.",
            "embedding": _generate_embedding(seed=23),
        },
        {
            "id": 3,
            "title": "Vector Search",
            "content": "Vector databases enable semantic search and retrieval augmented generation.",
            "embedding": _generate_embedding(seed=37),
        },
        {
            "id": 4,
            "title": "Hybrid Retrieval",
            "content": "Hybrid search blends full-text matching with ANN vector retrieval for relevance.",
            "embedding": _generate_embedding(seed=51),
        },
    ]


def demo7_seekdb_vec_search_with_sql(topk: int = 3):
    with engine_conn() as conn:
        print("[Demo7] SeekDB SQL 混合检索示例 - 表:", TABLE_NAME)

        # 1) 删除旧表并创建包含全文索引和向量索引的表
        conn.execute(text(f"DROP TABLE IF EXISTS {TABLE_NAME}"))
        conn.execute(text(f"""
            CREATE TABLE {TABLE_NAME} (
                id INT PRIMARY KEY,
                title TEXT,
                content TEXT,
                embedding VECTOR({EMBED_DIM}),
                FULLTEXT INDEX idx_fts(content) WITH PARSER ik,
                VECTOR INDEX idx_vec (embedding) WITH(DISTANCE=l2, TYPE=hnsw, LIB=vsag)
            ) ORGANIZATION = HEAP
        """))

        # 2) 插入示例数据（向量列直接以 SQL 字面量形式写入）
        insert_sql = text(f"""
            INSERT INTO {TABLE_NAME} (id, title, content, embedding)
            VALUES (:id, :title, :content, :embedding)
        """)
        for doc in _seed_articles():
            conn.execute(
                insert_sql,
                {
                    "id": doc["id"],
                    "title": doc["title"],
                    "content": doc["content"],
                    "embedding": json.dumps(doc["embedding"]),
                },
            )
        print("✅ 已创建表并写入 4 条向量化文档。")

        # 3) 以 SQL 的方式执行全文 + 向量混合检索
        keywords = "database vector"
        query_vec = _generate_embedding(seed=999)
        hybrid_sql = text(f"""
            SELECT
                id,
                title,
                l2_distance(embedding, :query_embedding) AS vec_distance,
                MATCH(content) AGAINST(:keywords IN NATURAL LANGUAGE MODE) AS text_score
            FROM {TABLE_NAME}
            WHERE MATCH(content) AGAINST(:keywords IN NATURAL LANGUAGE MODE)
            ORDER BY vec_distance APPROXIMATE
            LIMIT :topk
        """)
        rows = conn.execute(
            hybrid_sql,
            {
                "query_embedding": json.dumps(query_vec),
                "keywords": keywords,
                "topk": topk,
            },
        ).fetchall()

        print("\n🔍 混合检索结果（按向量距离排序，同时要求文本命中）：")
        for row in rows:
            dist = row.vec_distance
            tscore = row.text_score
            dist_str = f"{dist:.4f}" if dist is not None else "N/A"
            tscore_str = f"{tscore:.4f}" if tscore is not None else "N/A"
            print(f"✅ id={row.id}, title='{row.title}', vec_distance={dist_str}, text_score={tscore_str}")

        # 4) 可选：清理表，避免污染后续实验
        conn.execute(text(f"DROP TABLE IF EXISTS {TABLE_NAME}"))


if __name__ == "__main__":
    demo7_seekdb_vec_search_with_sql(topk=3)
