"""SQL 方言归一:进引擎前把 SQL 统一成目标方言。

LLM 被要求按目标方言生成,但不保证听话(它更熟 MySQL)。所以分三层:
  1) 目标方言能解析、且 AST 里没有 MySQL 专属痕迹 → 只做规范化(顺带压掉多余空格/大小写差异)
  2) 目标方言解析失败,或残留 MySQL 专属函数 → 当作 MySQL 重新解析再转译过去
  3) 转译也失败 → 原样返回,交给执行器报错,别在这里把 SQL 弄丢

为什么不能"先按目标方言解析"。实测(sqlglot 30.24):
  parse_one("SELECT DATE_FORMAT(order_date,'%Y-%m') ...", read="sqlite").sql("sqlite")
  → 仍是 DATE_FORMAT(未知函数被当成 Anonymous 原样保留),执行时 "no such function: DATE_FORMAT";
  CONCAT 更隐蔽:sqlite 解析器认得 exp.Concat,生成器却照样吐出 CONCAT(...)(SQLite 没有该函数)。
所以"能解析"不等于"目标方言能跑",必须再探一次 AST。
"""
import sqlglot
from sqlglot import expressions as exp

# 出现在 Anonymous 节点里、且确定是 MySQL 专属的函数名(小写比较)
_MYSQL_ONLY_FUNCS = {
    "date_format", "curdate", "curtime", "now", "unix_timestamp", "from_unixtime",
    "date_sub", "date_add", "str_to_date", "substring_index", "timestampdiff",
    "locate", "if", "ifnull", "last_day", "convert_tz", "week", "quarter",
    "dayofweek", "dayofmonth", "dayofyear", "time_to_sec", "period_diff",
}


def _needs_mysql_rewrite(stmt) -> bool:
    """AST 里是否残留 MySQL 专属痕迹(sqlite 跑不了)。"""
    for fn in stmt.find_all(exp.Anonymous):
        if fn.name.lower() in _MYSQL_ONLY_FUNCS:
            return True
    # CONCAT 在 SQLite 里不是函数,是 || 运算符
    return stmt.find(exp.Concat) is not None


def _transpile(sql: str, read: str, write: str) -> str | None:
    """解析+转译;任何异常都吞掉并返回 None(调用方决定怎么兜底)。"""
    try:
        out = sqlglot.transpile(sql, read=read, write=write)
    except Exception:
        return None
    return out[0] if out else None


def ensure_dialect(sql: str, dialect: str = "mysql") -> str:
    """把 sql 归一成 dialect。解析失败/无法转译时返回可用的最优结果,不抛异常。"""
    target = (dialect or "mysql").lower()
    if target == "mysql":
        return _transpile(sql, "mysql", "mysql") or sql

    stmt = None
    try:
        stmt = sqlglot.parse_one(sql, read=target)
    except Exception:
        stmt = None

    if stmt is not None and not _needs_mysql_rewrite(stmt):
        try:
            return stmt.sql(dialect=target)
        except Exception:
            pass

    rewritten = _transpile(sql, "mysql", target)
    if rewritten:
        # 已知代价:若一条 SQL 里同时有 MySQL 函数和 ||(混合方言),
        # 这里按 MySQL 解析会把 || 读成 OR。靠 prompt 声明方言 + 单一风格规避。
        return rewritten
    if stmt is not None:
        try:
            return stmt.sql(dialect=target)
        except Exception:
            pass
    return sql
