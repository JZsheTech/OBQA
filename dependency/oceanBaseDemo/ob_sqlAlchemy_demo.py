from sqlalchemy import create_engine, text

# 方案 A：MySQL 方言 + PyMySQL（通用）
engine = create_engine("mysql+pymysql://paperQA%40test:12345678@127.0.0.1:2881/obqademo", future=True)

with engine.begin() as conn:
    # 删除可能已存在的表，保证用例自洽
    conn.execute(text("DROP TABLE IF EXISTS t"))
    conn.execute(text("DROP TABLE IF EXISTS users"))
    conn.execute(text("DROP TABLE IF EXISTS dept"))

    # 创建 t 表、插入数据
    conn.execute(text("CREATE TABLE t(a INT PRIMARY KEY, b VARCHAR(50))"))
    conn.execute(text("INSERT INTO t(a,b) VALUES (1,'x'), (2,'y')"))

    # where + projection 示例
    rows = conn.execute(text("SELECT a FROM t WHERE b=:b"), {"b": "x"}).all()
    print("t 表中 b='x' 的记录 a 值：", rows)

    # 创建 users 和 dept 表，并插入示例数据，作为 join 的准备
    conn.execute(text("""
        CREATE TABLE dept (
            id   INT PRIMARY KEY,
            name VARCHAR(50)
        )
    """))
    conn.execute(text("""
        CREATE TABLE users (
            id      INT PRIMARY KEY,
            name    VARCHAR(50),
            dept_id INT,
            FOREIGN KEY (dept_id) REFERENCES dept(id)
        )
    """))
    # 插入 dept 和 users 的数据
    conn.execute(text("INSERT INTO dept(id,name) VALUES (10,'Sales'), (20,'Engineering')"))
    conn.execute(text("INSERT INTO users(id,name,dept_id) VALUES (100,'Alice',10), (101,'Bob',20)"))

    # join 示例
    result = conn.execute(text("""
        SELECT u.id AS user_id,
               u.name AS user_name,
               d.name AS dept_name
        FROM users u
        JOIN dept d ON u.dept_id = d.id
    """)).all()
    print("JOIN 查询结果：", result)

    # 删除 t 表中 a=2 的记录
    conn.execute(text("DELETE FROM t WHERE a=2"))
    print("删除 a=2 后，t 表剩余记录：", conn.execute(text("SELECT * FROM t")).all())
