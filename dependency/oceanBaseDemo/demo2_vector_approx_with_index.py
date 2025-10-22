# dependency/oceanBaseDemo/demo2_vector_approx_with_index.py
import random
from sqlalchemy import func

from ob_vector_utils import (
    OB_DEMO_TABLE,
    ensure_pyobvector_client,
    engine_conn,
    drop_demo_table,
    create_demo_table,
)

def demo_vector_approx_with_index():
    tbl = OB_DEMO_TABLE
    print(f"\n[Demo2] 向量近似检索（带索引）- 表: {tbl}")

    client = ensure_pyobvector_client()

    # 1) 建表（先清理再建）
    with engine_conn() as conn:
        create_demo_table(conn, table_name=tbl)
        print(f"✅ 已创建并清空表: {tbl}")

    # 2) 创建向量近似索引（HNSW 例子）
    print("→ 正在创建向量索引 (HNSW) …")
    client.create_index(
        table_name=tbl,
        is_vec_index=True,
        index_name=f"{tbl}_vidx",
        column_names=["embedding"],
        vidx_params="distance=l2, type=hnsw, lib=vsag,  m=16, ef_construction=256"
    )
    print("✅ 向量索引创建完成。")

    # 3) 批量插入数据
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
            print(f"→ 插入 {batch_size} 条，进度 id ≤ {i + 1}")
            batch = []
    if batch:
        client.insert(tbl, data=batch)
        print(f"→ 插入剩余 {len(batch)} 条，进度 id ≤ {total}")

    print(f"✅ 共插入 {total} 条数据到 {tbl}")

    # 4) ANN 近似检索
    query_vec = [random.uniform(-1, 1) for _ in range(64)]
    res = client.ann_search(
        table_name=tbl,
        vec_data=query_vec,
        vec_column_name="embedding",
        distance_func=func.l2_distance,            # ✅ 你的规范写法
        with_dist = True,
        topk=5,
        output_column_names=["id", "title", "tag", "embedding"],
    )

    print("\nTop-5 相似结果：")
    for i, r in enumerate(res, 1):
        rid = r.id 
        # debug_flag1 = input("stop")
        rtitle = r.title
        rtag = r.tag
        dist = r[-1] # pyobvector接口取最后一个元素作为距离值
        if dist is not None:
            print(f"{i}. id={rid}, title={rtitle}, tag={rtag}, distance={dist}")
        else:
            print(f"{i}. id={rid}, title={rtitle}, tag={rtag}")

    # 测试结束：删除表
    with engine_conn() as conn:
        drop_demo_table(conn, table_name=tbl)

if __name__ == "__main__":
    demo_vector_approx_with_index()
