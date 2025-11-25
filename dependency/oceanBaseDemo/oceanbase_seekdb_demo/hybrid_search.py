# hybrid_search_demo.py

"""
示例：使用 SQLAlchemy 连接 seekdb，并演示混合检索（full-text + vector）。
注意：请先确认数据库支持 VECTOR 类型、FULLTEXT INDEX 等。
"""

import os
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import text

# —— 配置部分 —— 
DB_USER = os.getenv("SEEKDB_USER", "user")
DB_PASS = os.getenv("SEEKDB_PASS", "password")
DB_HOST = os.getenv("SEEKDB_HOST", "127.0.0.1")
DB_PORT = os.getenv("SEEKDB_PORT", "3306")  # 或 seekdb 默认端口
DB_NAME = os.getenv("SEEKDB_DB", "testdb")

# MySQL兼容连接字符串
connection_str = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
engine = create_engine(connection_str, echo=True, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# —— 模型定义 —— 
class DocTable(Base):
    __tablename__ = "doc_table"
    c1 = Column(Integer, primary_key=True, autoincrement=False)
    # 注意：SQLAlchemy 默认没有 VECTOR 类型。这里暂用 String/Text 来插入 vector 常量字符串
    vector = Column(String(255))  
    query = Column(String(255))
    content = Column(String(255))

# —— 初始化表（如不存在） —— 
def init_db():
    Base.metadata.create_all(bind=engine)
    # 创建索引及向量索引、全文索引，通常需要 raw SQL
    with engine.begin() as conn:
        # 如果这些索引已创建，可跳过
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS doc_table (
              c1 INT,
              vector VECTOR(3),
              query VARCHAR(255),
              content VARCHAR(255),
              PRIMARY KEY (c1)
            );
        """))
        conn.execute(text("""
            CREATE VECTOR INDEX IF NOT EXISTS idx1 ON doc_table(vector) 
              WITH (distance = l2, type = hnsw, lib = vsag);
        """))
        conn.execute(text("""
            CREATE FULLTEXT INDEX IF NOT EXISTS idx2 ON doc_table(query);
        """))
        conn.execute(text("""
            CREATE FULLTEXT INDEX IF NOT EXISTS idx3 ON doc_table(content);
        """))
    print("Initialized doc_table with indexes.")

# —— 插入示例数据 —— 
def insert_sample_data():
    with engine.begin() as conn:
        # 删除旧数据
        conn.execute(text("TRUNCATE TABLE doc_table;"))
        # 插入数据 （参考文档） 
        conn.execute(text("""
            INSERT INTO doc_table VALUES
            (1, '[1,2,3]', "hello world", "oceanbase Elasticsearch database"),
            (2, '[1,2,1]', "hello world, what is your name", "oceanbase mysql database"),
            (3, '[1,1,1]', "hello world, how are you", "oceanbase oracle database"),
            (4, '[1,3,1]', "real world, where are you from", "postgres oracle database"),
            (5, '[1,3,2]', "real world, how old are you", "redis oracle database"),
            (6, '[2,1,1]', "hello world, where are you from", "starrocks oceanbase database");
        """))
    print("Inserted sample data.")

# —— 执行混合检索 —— 
def hybrid_search(keyword_query: str, vector_query: list, k: int = 5, boost_text: float = 2.0, boost_vector: float = 1.0):
    """
    执行混合检索：
      - keyword_query: 用于全文检索的字符串
      - vector_query: 用于向量检索的 list，须与 vector 列维度保持一致
      - k: 返回 top-k 向量结果
      - boost_text: 文本检索权重
      - boost_vector: 向量检索权重
    """
    import json
    param = {
        "query": {
            "query_string": {
                "fields": ["query", "content"],
                "query": keyword_query,
                "boost": boost_text
            }
        },
        "knn": {
            "field": "vector",
            "k": k,
            "query_vector": vector_query,
            "boost": boost_vector
        }
    }
    param_str = json.dumps(param)
    sql = f"SELECT JSON_PRETTY(DBMS_HYBRID_SEARCH.SEARCH('doc_table', '{param_str}'));"
    with engine.begin() as conn:
        result = conn.execute(text(sql))
        rows = result.fetchall()
        for row in rows:
            print(row[0])
    print("Hybrid search done.")

# —— 主流程 —— 
if __name__ == "__main__":
    init_db()
    insert_sample_data()
    # 示例：全文关键词 “hello oceanbase”，向量 [1,2,3]
    hybrid_search(keyword_query="hello oceanbase", vector_query=[1,2,3], k=5, boost_text=2.0, boost_vector=1.0)
