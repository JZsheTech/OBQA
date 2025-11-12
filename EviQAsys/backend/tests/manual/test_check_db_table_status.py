
from pathlib import Path

PROJECT_ROOT_DIR = Path(__file__).resolve().parents[4]
import sys
sys.path.append(str(PROJECT_ROOT_DIR))
from EviQAsys.backend.app.repositories.db_stats import print_table_stats

print_table_stats()  # 或传入自定义的表名列表
