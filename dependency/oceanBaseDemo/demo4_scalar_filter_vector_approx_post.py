# dependency/oceanBaseDemo/demo4_scalar_filter_vector_approx_post.py
import random
from sqlalchemy import func, text

from ob_vector_utils import (
    OB_DEMO_TABLE,
    ensure_pyobvector_client,
    engine_conn,
    drop_demo_table,
    create_demo_table,
)

def demo_scalar_filter_vector_approx_post():
    tbl = OB_DEMO_TABLE + "_mix_approx"
    print(f"\n[Demo4] 标量过滤 + 向量近似检索（后过滤）- 表: {tbl}")

    client = ensure_pyobvector_client()

    # 1️⃣ 建表
    with engine_conn() as conn:
        create_demo_table(conn, table_name=tbl)
        print(f"✅ 已创建表 {tbl}")

    # 2️⃣ 创建向量索引
    print("→ 正在创建向量索引 (HNSW)…")
    client.create_index(
        table_name=tbl,
        is_vec_index=True,
        index_name=f"{tbl}_vidx",
        column_names=["embedding"],
        vidx_params="distance=l2, type=hnsw, lib=vsag, m=16, ef_construction=256"
    )
    print("✅ 向量索引创建完成。")

    # 3️⃣ 插入数据
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
    print(f"✅ 共插入 {total} 条数据。")

    # 4️⃣ 向量近似检索 + 标量过滤（post-search）
    query_vec = [random.uniform(-1, 1) for _ in range(64)]
    print("→ 仅在 tag='cv' 的子集上执行近似向量匹配 (post-search)…")

    res = client.post_ann_search(
        table_name=tbl,
        vec_data=query_vec,
        vec_column_name="embedding",
        distance_func=func.l2_distance,
        with_dist=True,
        topk=5,
        output_column_names=["id", "title", "tag"],
        where_clause=[text("tag = 'cv'")],
    )

    print("\nTop-5 相似结果 (tag='cv')：")
    for i, r in enumerate(res, 1):
        rid = r.id
        rtitle = r.title
        rtag = r.tag
        dist = r[-1]
        print(f"{i}. id={rid}, title={rtitle}, tag={rtag}, distance={dist}")

    # 5️⃣ 清理
    with engine_conn() as conn:
        drop_demo_table(conn, table_name=tbl)

if __name__ == "__main__":
    demo_scalar_filter_vector_approx_post()
