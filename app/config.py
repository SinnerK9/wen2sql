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

# 执行引擎:sqlite(默认,零配置可跑) / mysql(真库) / stub(联调假数据)
EXEC_ENGINE = os.environ.get("EXEC_ENGINE", "sqlite")

# SQLite 库文件(coffee 库)
SQLITE_DB = Path(os.environ.get("SQLITE_DB", DB_DIR / "coffee.db"))

# 引擎 → SQL 方言:唯一来源,executor(prompt/校验/执行)都从这里取,避免两处映射漂移
ENGINE_DIALECT = {"sqlite": "sqlite", "mysql": "mysql", "stub": "mysql"}
# 方言一般由引擎决定,只有特殊场景才需要手动覆盖(如 sqlite 引擎上故意生成 MySQL 语法)
DB_DIALECT = os.environ.get("DB_DIALECT", ENGINE_DIALECT.get(EXEC_ENGINE, "sqlite"))

KNOWLEDGE_JSON = DATA_DIR / "knowledge.json"
