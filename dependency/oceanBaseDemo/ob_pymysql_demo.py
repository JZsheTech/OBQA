import pymysql
from datetime import datetime

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

conn = pymysql.connect(
    host="127.0.0.1", port=2881,
    user="paperQA@test", password="12345678",
    database="", charset="utf8mb4",
    autocommit=True
)
cur = conn.cursor()

try:
    # 1) 建库
    log("创建数据库 obqademo（如果不存在）...")
    cur.execute("CREATE DATABASE IF NOT EXISTS obqademo DEFAULT CHARACTER SET utf8mb4")
    log("✅ 数据库创建完成。")

    # 切换库
    cur.execute("USE obqademo")
    log("切换至数据库 obqademo。")

    # 2) 建表
    log("创建表 users 和 dept（如果不存在）...")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
      id BIGINT PRIMARY KEY AUTO_INCREMENT,
      name VARCHAR(100) NOT NULL,
      dept_id BIGINT,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS dept (
      id BIGINT PRIMARY KEY AUTO_INCREMENT,
      name VARCHAR(100) NOT NULL
    )
    """)
    log("✅ 表创建完成。")

    # 3) 插入
    log("插入示例数据到 dept 表...")
    cur.execute("INSERT INTO dept(name) VALUES ('AI Lab'),('DB Group')")
    cur.execute("SELECT * FROM dept")
    log(f"dept 表当前内容：{cur.fetchall()}")

    log("插入示例数据到 users 表...")
    cur.execute("INSERT INTO users(name, dept_id) VALUES (%s, %s)", ("Alice", 1))
    cur.execute("INSERT INTO users(name, dept_id) VALUES (%s, %s)", ("Bob", 2))
    cur.execute("SELECT * FROM users")
    log(f"users 表当前内容：{cur.fetchall()}")

    # 4) 查询（投影 + where）
    log("查询：name LIKE '%A%' 的用户：")
    cur.execute("SELECT id, name FROM users WHERE name LIKE %s", ("%A%",))
    for row in cur.fetchall():
        log(f"→ 用户记录: {row}")

    # 5) join 查询
    log("执行 JOIN 查询 (users ↔ dept)...")
    cur.execute("""
    SELECT u.id, u.name, d.name AS dept_name
    FROM users u JOIN dept d ON u.dept_id = d.id
    """)
    join_rows = cur.fetchall()
    log("JOIN 查询结果：")
    for r in join_rows:
        log(f"→ {r}")

    # 6) 删除 / 更新
    log("删除用户 Bob...")
    cur.execute("DELETE FROM users WHERE name=%s", ("Bob",))
    cur.execute("SELECT * FROM users")
    log(f"users 表删除后内容：{cur.fetchall()}")

    log("更新用户 Alice → Alice Zhang...")
    cur.execute("UPDATE users SET name=%s WHERE id=%s", ("Alice Zhang", 1))
    cur.execute("SELECT * FROM users")
    log(f"users 表更新后内容：{cur.fetchall()}")

except Exception as e:
    log(f"❌ 出错: {e}")

finally:
    cur.close()
    conn.close()
    log("数据库连接已关闭。")
