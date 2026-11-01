import sqlglot
from sqlglot import expressions as exp
def truncate(sql:str, dialect: str = "mysql") -> str:
    try:
        stmt = sqlglot.parse_one(sql, read=dialect)
    except Exception:
        # 解析失败，直接包一层COUNT
        return f"SELECT COUNT(*) FROM ({sql}) AS subq"
    # 解析结果得到语句属于SELECT，去掉validate加入的limit和order
    if isinstance(stmt, exp.Select):
        stmt.args.pop("limit", None)
        stmt.args.pop("offset", None)
        stmt.args.pop("order", None)
        sql_final = stmt.sql(dialect=dialect)
    # 解析结果不属于SELECT，直接放上去
    else:
        sql_final = sql

    return f"SELECT COUNT(*) FROM ({sql_final}) AS subq"

# 给SQL句子加上超时hint
def with_timeout(sql, timeout_ms, dialect: str = "mysql") -> str:
    # MAX_EXECUTION_TIME 是 MySQL 专属:SQLite 会当注释或直接语法错,
    # 它的超时靠 sqlite_engine 的 progress_handler,所以非 mysql 原样返回
    if dialect != "mysql":
        return sql
    try:
        stmt = sqlglot.parse_one(sql, read=dialect)
    # 解析失败，直接返回原SQL语句
    except Exception:
        return sql
    if isinstance(stmt, exp.Select):
        stmt.args['hint']  = exp.Hint(
            expressions = [exp.Anonymous(
                this = 'MAX_EXECUTION_TIME',
                expressions = [exp.Literal.number(timeout_ms)]
            )]
        )
        return stmt.sql(dialect=dialect)
    else:
        return sql

    
