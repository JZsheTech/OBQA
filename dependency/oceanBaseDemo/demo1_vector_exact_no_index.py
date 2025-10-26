# dependency/oceanBaseDemo/demo1_vector_exact_no_index_fixed.py
import random
from sqlalchemy import func

from ob_vector_utils import (
    OB_DEMO_TABLE,
    ensure_pyobvector_client,
    engine_conn,
    drop_demo_table,
    create_demo_table,
)


def demo_vector_exact_no_index():
    tbl = OB_DEMO_TABLE
    print(f"\n[Demo1] 向量精确检索（无索引）- 表: {tbl}")

    # 测试开始：先清理再建表
    with engine_conn() as conn:
        create_demo_table(conn, table_name=tbl)

    client = ensure_pyobvector_client()

    # 2️⃣ 插入数据
    random.seed(20241023)
    batch_size = 100
    batch = []
    for i in range(500):
        batch.append({
            "id": i + 1,
            "title": f"Paper_{i}",
            "tag": random.choice(["nlp", "cv", "db"]),
            "embedding": [random.uniform(-1, 1) for _ in range(64)]
        })
        if len(batch) == batch_size:
            client.insert(tbl, data=batch)
            batch = []
    if batch:
        client.insert(tbl, data=batch)

    print(f"✅ 已插入 500 条记录到表 {tbl}")

    # 3️⃣ 查询（Top-5 最近向量）
    query_vec = [random.uniform(-1, 1) for _ in range(64)]

    # res = client.post_ann_search 先标量过滤，再ann后过滤。
    res = client.precise_search(
        table_name=tbl,
        vec_data=query_vec,
        vec_column_name="embedding",
        distance_func=func.l2_distance,
        topk=5,
        output_column_names=["id", "title", "tag", "embedding"],
    ) # 混合检索时可以带 where_clause

    print("\nTop-5 相似结果：")
    for r in res:
        print(r)

    # 测试结束：删除表，保持干净
    with engine_conn() as conn:
        drop_demo_table(conn, table_name=tbl)

if __name__ == "__main__":
    demo_vector_exact_no_index()
