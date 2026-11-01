import sqlglot
from sqlglot import expressions as exp
def truncate(sql:str) -> str:
    try:
        stmt = sqlglot.parse_one(sql, read="mysql")
    except Exception:
        # 解析失败，直接包一层COUNT
        return f"SELECT COUNT(*) FROM ({sql}) AS subq"
    # 解析结果得到语句属于SELECT，去掉validate加入的limit和order
    if isinstance(stmt, exp.Select):
        stmt.args.pop("limit", None)
        stmt.args.pop("offset", None)
        stmt.args.pop("order", None)
        sql_final = stmt.sql(dialect="mysql")
    # 解析结果不属于SELECT，直接放上去
    else:
        sql_final = sql

    return f"SELECT COUNT(*) FROM ({sql_final}) AS subq"

# 给SQL句子加上超时hint
def with_timeout(sql, timeout_ms) -> str:
    try:
        stmt = sqlglot.parse_one(sql, read="mysql")
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
        return stmt.sql(dialect="mysql")
    else:
        return sql

    
