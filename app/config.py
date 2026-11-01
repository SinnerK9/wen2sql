import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_DIR = ROOT / "coffee_db"

SCHEMA_SQL = Path(os.environ.get("SCHEMA_SQL",DB_DIR / "coffee_schema.sql"))
SCHEMA_JSON = Path(os.environ.get("SCHEMA_JSON",DATA_DIR / "schema.json"))

# MySQL(真库,来自 .env;没配则走文件解析)
MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
MYSQL_USER = os.environ.get("MYSQL_USER", "")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
MYSQL_DB = os.environ.get("MYSQL_DB", "coffee")

# LLM(mock 无 key 可跑;接真 LLM 配 .env)
LLM_MODE = os.environ.get("LLM_MODE", "mock")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "")
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0"))

# 执行引擎:mysql=真库(需账号) / stub=固定假数据(链路联调用)
EXEC_ENGINE = os.environ.get("EXEC_ENGINE", "stub")

KNOWLEDGE_JSON = DATA_DIR / "knowledge.json"
