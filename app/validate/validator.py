"""sqlglot AST 硬校验 7 项。

  validate(sql, tables) -> (ok, errors, final_sql)
  - 拒绝型:只读 / 单语句 / 表白名单(排除CTE)/ 限联表数 / 危险函数 / 列校验
  - 改写型:LIMIT 分级(无界明细强制注入 LIMIT,高基数聚合不硬顶)
  参考:开源 text2sql 项目里校验层的常见做法(只读检查、从 SQL 提取表名时排除 CTE)。
  修正(2026-08):_real_tables 去重 + CTE 作用域;LIMIT 子查询聚合不误豁免;UNION 补 LIMIT。
"""

import sqlglot
from sqlglot import expressions as exp
from app.constants import DEFAULT_LIMIT

MAX_TABLES = 8 # 限制联表数上限为8
EXPECTED_SCHEMA = "" # 可选 schema 白名单(如 "coffee");空 = 不校验

# 定义MySQL危险函数
DANGEROUS_FUNCS = {
    "LOAD_FILE", "SLEEP", "BENCHMARK", "GET_LOCK", "RELEASE_LOCK",
}

# 沿 .parent 链向上走,返回所有祖先(不依赖 .parents 属性,兼容所有节点类型)
def _ancestors(node):
    p = getattr(node, "parent", None)
    while p is not None:
        yield p
        p = p.parent

# 提取真实表，排除CTE(返回set去重;CTE名只在外层FROM生效,body内同名的是真表)
def _real_tables(stmt) -> set:
    ctes = set()
    # sqlglot对with语句存为exp.With
    for w in stmt.find_all(exp.With):
        for cte in w.expressions:
            ctes.add(cte.alias_or_name) # cte.alias_or_name优先返回 alias（别名），如果 alias 为空则返回 name
    real = set()
    for t in stmt.find_all(exp.Table):
        name = t.name
        # 简化实现:如果表名在 ctes 中，且该表节点的祖先中有 exp.With，则视为真实表,后续优化
        if name in ctes:
            if any(isinstance(p, exp.With) for p in _ancestors(t)):
                real.add(name)
        else:
            real.add(name)
    return real

def _check_read_only(stmt, tables) -> str:
    """只允许SELECT(含 UNION/EXCEPT/INTERSECT 等只读复合查询)"""
    if isinstance(stmt, (exp.Select, exp.Union, exp.Except, exp.Intersect)):
        return ""
    if isinstance(stmt, exp.With):
        return _check_read_only(stmt.this, tables)
    return "只允许 SELECT 查询"

def _check_tables(stmt, tables) -> str:
    """表白名单 + 限联表数。"""
    allowed = set(tables.keys())
    real = _real_tables(stmt)
    for t in stmt.find_all(exp.Table):
        if EXPECTED_SCHEMA and t.db and t.db != EXPECTED_SCHEMA:
            return f"引用了其他 schema 的表: {t.db}.{t.name}"
    for name in real:
        if name not in allowed:
            return f"引用了未授权表: {name}"
    if len(real) > MAX_TABLES:
        return f"联表数超过上限 {MAX_TABLES}"
    return ""

def _check_dangerous(stmt, tables) -> str:
    """禁止危险函数"""
    for fn in stmt.find_all(exp.Anonymous):
        if fn.name.upper() in DANGEROUS_FUNCS:
            return f"检测到危险函数: {fn.name}"
    return ""

def _check_columns(stmt, tables) -> str:
    """schema-aware 列校验(拦"合法但写错"的列名;支持表别名)。"""
    real_tables = _real_tables(stmt)
    table_cols = {name: set(tables.get(name, {}).get("columns", {}).keys())
                  for name in real_tables}
    # 别名(或未起别名的表名)→ 真实表名;引用了 CTE/子查询别名等对不上基表的,不在映射里
    alias_map = {}
    for t in stmt.find_all(exp.Table):
        if t.name in real_tables:
            alias_map[t.alias or t.name] = t.name
    aliases = set()
    for sel in stmt.find_all(exp.Select):
        for proj in sel.expressions:
            if isinstance(proj, exp.Alias):
                aliases.add(proj.alias)
    for col in stmt.find_all(exp.Column):
        if col.name in aliases:
            continue
        if col.table:
            real = alias_map.get(col.table)
            if real is None:
                # 限定符是 CTE 名 / 子查询别名等,无法对基表校验,跳过
                continue
            if col.name not in table_cols.get(real, set()):
                return f"列 {col.name} 在表 {real}(别名 {col.table}) 中不存在"
        else:
            if not any(col.name in cols for cols in table_cols.values()):
                return f"列 {col.name} 不存在"
    return ""

# ⑤ LIMIT 分级(改写型) 
def _has_agg_here(stmt) -> bool:
    """只看当前SELECT层级的聚合,不递归进子查询(子查询里的聚合不豁免外层)。"""
    for agg in stmt.find_all(exp.AggFunc):
        if any(isinstance(p, exp.Subquery) for p in _ancestors(agg)):
            continue
        return True
    return False

def _select_is_unbounded(sel) -> bool:
    """当前SELECT是否"无界明细":无分组/聚合/去重,且无LIMIT。"""
    if sel.args.get("group") is not None:
        return False
    if sel.args.get("distinct") is not None:
        return False
    if _has_agg_here(sel):
        return False
    return sel.args.get("limit") is None

def _leaf_selects(node) -> list:
    """展开UNION等复合查询,取所有叶子SELECT(UNION也要补LIMIT)。"""
    if isinstance(node, exp.Select):
        return [node]
    if isinstance(node, exp.Union):
        return _leaf_selects(node.this) + _leaf_selects(node.expression)
    return []

def _apply_limit(stmt) -> None:
    # sqlglot 的 .limit() 默认返回副本,copy=False原地改
    if isinstance(stmt, exp.Union):
        # UNION:任一支是无界明细都可能导致结果很大 → 给整个UNION补LIMIT
        if stmt.args.get("limit") is None and any(
                _select_is_unbounded(s) for s in _leaf_selects(stmt)):
            stmt.limit(DEFAULT_LIMIT, copy=False)
        return
    if isinstance(stmt, exp.Select) and _select_is_unbounded(stmt):
        stmt.limit(DEFAULT_LIMIT, copy=False)

def validate(sql: str, tables: dict) -> tuple[bool, list, str]:
    """单语句 + 编排。返回 (是否通过, 错误列表, 改写后的SQL)。"""
    try:
        stmts = sqlglot.parse(sql, read="mysql")
    except Exception as e:
        return False, [f"SQL 解析失败: {e}"], sql

    if len(stmts) != 1:
        return False, ["单语句校验失败: 不支持多条语句"], sql
    stmt = stmts[0]

    errors = []
    for check in (_check_read_only, _check_tables, _check_dangerous, _check_columns):
        msg = check(stmt, tables)
        if msg:
            errors.append(msg)

    if errors:
        return False, errors, sql

    _apply_limit(stmt)
    return True, [], stmt.sql(dialect="mysql")
