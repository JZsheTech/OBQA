# dependency/oceanBaseDemo/demo3_scalar_filter_vector_exact.py
import random
from sqlalchemy import func, text

from ob_vector_utils import (
    OB_DEMO_TABLE,
    ensure_pyobvector_client,
    engine_conn,
    drop_demo_table,
    create_demo_table,
)

def demo_scalar_filter_vector_exact():
    tbl = OB_DEMO_TABLE + "_mix_exact"
    print(f"\n[Demo3] 标量过滤 + 向量精确检索（预过滤）- 表: {tbl}")

    client = ensure_pyobvector_client()

    # 1️⃣ 建表（先清理再建）
    with engine_conn() as conn:
        create_demo_table(conn, table_name=tbl)
        print(f"✅ 已创建表 {tbl}")

    # 2️⃣ 插入数据
    random.seed(20241023)
    total = 500
    batch_size = 100
    batch = []
    for i in range(total):
        batch.append({
            "id": i + 1,
            "title": f"Paper_{i}",
            "tag": random.choice(["nlp", "cv", "db"]),
            "embedding": [random.uniform(-1, 1) for _ in range(64)],
        })
        if len(batch) == batch_size:
            client.insert(tbl, data=batch)
            batch = []
    if batch:
        client.insert(tbl, data=batch)
    print(f"✅ 插入 {total} 条数据到 {tbl}")

    # 3️⃣ 精确检索 + 标量过滤
    query_vec = [random.uniform(-1, 1) for _ in range(64)]
    print("→ 仅检索 tag='nlp' 的子集 (预过滤)...")

    res = client.precise_search(
        table_name=tbl,
        vec_data=query_vec,
        vec_column_name="embedding",
        distance_func=func.l2_distance,
        topk=5,
        output_column_names=["id", "title", "tag"],
        where_clause=[text("tag = 'nlp'")],
    )

    print("\nTop-5 相似结果 (tag='nlp')：")
    for i, r in enumerate(res, 1):
        print(f"{i}. id={r.id}, title={r.title}, tag={r.tag}")

    # 4️⃣ 清理
    with engine_conn() as conn:
        drop_demo_table(conn, table_name=tbl)

if __name__ == "__main__":
    demo_scalar_filter_vector_exact()
