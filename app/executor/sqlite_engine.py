"""SQLite 执行器:只读连接 + 截断可见化 + 真实总数 + 超时中断。

与 executor._run(mysql) 保持同一返回形状:(columns, rows, truncated, total)。
差异点:SQLite 没有服务端超时,只能用 progress_handler 主动中断。
"""
import sqlite3
import time

from app import config
from app.constants import EXEC_TIMEOUT, MAX_ROWS
from app.executor.truncate import truncate


def _connect() -> sqlite3.Connection:
    # mode=ro:数据库层只读。和 MySQL 只读账号是同一道防线——
    # 校验器只保证「结构上不危险」,真正的写入拦截靠权限层(不赌校验器)。
    # as_posix():URI 里用正斜杠,Windows 反斜杠在部分 sqlite 版本上解析不稳。
    if not config.SQLITE_DB.exists():
        # sqlite 自己只会报 "unable to open database file",看不出是缺库还是路径错
        raise FileNotFoundError(
            f"SQLite 库文件不存在: {config.SQLITE_DB}（先跑 coffee_db/build_coffee.py 造数）"
        )
    return sqlite3.connect(f"file:{config.SQLITE_DB.as_posix()}?mode=ro", uri=True)


def fetch_sqlite(sql: str) -> tuple[list[str], list[tuple], bool, int]:
    conn = _connect()
    deadline = time.monotonic() + EXEC_TIMEOUT

    def _guard() -> int:
        # 每执行 N 条 VM 指令回调一次;返回非 0 直接中止查询
        return 1 if time.monotonic() > deadline else 0

    # 10_000 是回调频率:太小拖慢查询,太大中断不及时
    conn.set_progress_handler(_guard, 10_000)
    try:
        cur = conn.execute(sql)
        if cur.description is None:
            # 非结果集语句(如 PRAGMA 写法/DDL);校验器本该拦住,这里兜底不给空表
            raise ValueError("该 SQL 不返回结果集")
        columns = [d[0] for d in cur.description]
        rows = cur.fetchmany(MAX_ROWS)          # 先拿 MAX_ROWS 行
        if cur.fetchone() is None:              # 再探一条:拿不到 = 没截断
            return columns, list(rows), False, len(rows)
        # 确实截断:去掉 LIMIT/ORDER 包一层 COUNT,拿真实总数(复用 truncate)
        count_sql = truncate(sql, dialect="sqlite")
        total = conn.execute(count_sql).fetchone()[0]
        return columns, list(rows), True, total
    except sqlite3.OperationalError as e:
        if "interrupt" in str(e).lower():
            raise TimeoutError(
                f"执行超时（>{EXEC_TIMEOUT}s），查询可能太复杂，请换更简单的问法"
            ) from e
        raise
    finally:
        conn.close()
