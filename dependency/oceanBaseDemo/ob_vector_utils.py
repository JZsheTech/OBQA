# dependency/oceanBaseDemo/ob_vector_utils.py
import uuid
from sqlalchemy import create_engine, text
from contextlib import contextmanager
from pyobvector import ObVecClient

# ---------- 连接参数 ----------
DSN = "mysql+pymysql://root:@127.0.0.1:2893/test?charset=utf8mb4"
OB_HOST = "127.0.0.1:2893"
OB_USER = "root"
OB_DB   =  "test"
OB_PASS = ""

# 固定用于 Demo 的表名（避免随机表名造成脏数据）
OB_DEMO_TABLE = "obqa_demo_vector"

@contextmanager
def engine_conn():
    """上下文：自动创建数据库并连接"""
    engine = create_engine(DSN, future=True)
    with engine.begin() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {OB_DB}"))
        conn.execute(text(f"USE {OB_DB}"))
    with engine.begin() as conn:
        yield conn

# 便捷工具：在测试前后清理表，保持数据库干净

def drop_demo_table(conn, table_name: str = OB_DEMO_TABLE):
    conn.execute(text(f"DROP TABLE IF EXISTS {table_name}"))


def create_demo_table(conn, table_name: str = OB_DEMO_TABLE):
    # 先删后建，确保全新表
    conn.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
    conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {table_name}(
              id BIGINT PRIMARY KEY,
              title VARCHAR(200),
              tag   VARCHAR(50),
              embedding VECTOR(64)
            )
        """))


def ensure_pyobvector_client() -> ObVecClient:
    """返回一个 ObVecClient 客户端"""
    return ObVecClient(uri=OB_HOST, user=OB_USER, db_name=OB_DB, password=OB_PASS)
