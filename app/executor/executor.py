from dataclasses import dataclass, field
from app import config
import pymysql
from app.constants import MAX_ROWS, EXEC_TIMEOUT
from app.executor.dialect import ensure_dialect
from app.executor.sqlite_engine import fetch_sqlite
from app.executor.truncate import truncate, with_timeout
from app.executor.stub import fetch_stub
from concurrent.futures import ThreadPoolExecutor

@dataclass
class Result:
    columns: list[str] = field(default_factory=list)
    rows: list[tuple] = field(default_factory=list)
    truncated: bool = False
    total: int | None = None

def execute(sql: str, engine: str = config.EXEC_ENGINE) -> Result:
    # 调用方只传 engine;方言由 config.ENGINE_DIALECT 映射,少一个必传参数就少一处不一致
    dialect = config.ENGINE_DIALECT.get(engine)
    if dialect is None:
        raise ValueError("数据库引擎不合法")
    # 进引擎前统一方言:LLM 写 MySQL 语法 + 引擎是 sqlite 是最可能的组合,靠这层兜底
    sql = ensure_dialect(sql, dialect)

    if engine == "sqlite":
        columns, rows, truncated, total = fetch_sqlite(sql)
    elif engine == "stub":
        columns, rows, truncated, total = fetch_stub(sql)
    else:
        columns, rows, truncated, total = fetch_mysql(sql)
    return Result(
        columns=columns,
        rows=rows,
        truncated=truncated,
        total=total,
    )

# 线程中的执行函数，自己建立连接自己关闭
def _run(sql: str) -> tuple[list[str], list[tuple], bool, int]:
    if not config.MYSQL_USER:
        raise ValueError("未配置 MYSQL_USER（请在 .env 或环境变量中设置 MySQL 账号）")
    conn = pymysql.connect(user=config.MYSQL_USER, database=config.MYSQL_DB,
                    host=config.MYSQL_HOST, port=config.MYSQL_PORT, password=config.MYSQL_PASSWORD, charset="utf8mb4")
    try:
        with conn.cursor() as cur:
            # 给sql加上超时hint
            sql = with_timeout(sql, EXEC_TIMEOUT * 1000)
            cur.execute(sql)
            columns = [d[0] for d in cur.description]
            rows = cur.fetchmany(MAX_ROWS)
            # 在1000行后确实有1001行，则说明出现截断
            if cur.fetchone() is not None:
                truncated = True
                # 确实出现截断，先把前面validate套上去的limit去了，以便后续得到total
                count_sql = truncate(sql)
                with conn.cursor() as count_cur:
                    count_cur.execute(count_sql)
                    total = count_cur.fetchone()[0]
            else:
                truncated = False
                total = len(rows)
            return (columns,list(rows), truncated, total)
    finally:
        conn.close()

# 建立线程池，将执行函数交给其他业务线程处理
def fetch_mysql(sql: str) -> tuple[list[str], list[tuple], bool, int]:
    ex = ThreadPoolExecutor(max_workers = 1)
    future = ex.submit(_run, sql)
    try:
        return future.result(timeout = EXEC_TIMEOUT)
    except TimeoutError:
        raise TimeoutError(f"执行超时（>{EXEC_TIMEOUT}s），查询可能太复杂，请换更简单的问法")
    finally:
         ex.shutdown(wait=False)
