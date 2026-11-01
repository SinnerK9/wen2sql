"""Prompt 构建:M-Schema 全量注入 + 注释清洗 + 方言声明。"""
from datetime import datetime

_DIALECT_NAME = {"sqlite": "SQLite 3", "mysql": "MySQL 8.0"}

# 方言提示:LLM 默认按 MySQL 习惯写 DATE_FORMAT / CONCAT / IF,在 SQLite 上必炸。
# 与其指望它「自己知道」,不如把该方言没有什么、该用什么写死进 prompt。
_DIALECT_HINT = {
    "sqlite": (
        "SQLite 方言:时间格式化用 STRFTIME('%Y-%m', 列),没有 DATE_FORMAT;"
        "字符串拼接用 ||,没有 CONCAT;条件用 IIF(条件, 真值, 假值),没有 IF;"
        "取整用 CAST(x AS INTEGER);时间一律写 'YYYY-MM-DD' 字面量,不要用 NOW()。"
    ),
    "mysql": (
        "MySQL 8.0 方言:时间格式化用 DATE_FORMAT(列, '%Y-%m');字符串拼接用 CONCAT。"
    ),
}

def _clean_comment(comment: str) -> str:
    # 枚举提示写在注释里,如 '会员等级：普通, 银卡, 金卡, 黑金',
    # 逗号会污染 M-Schema 的 (列: 类型, 注释) 结构,只保留冒号前的主语。
    # 注意:DDL 注释里的冒号可能是半角 ':' 也可能是全角 '：',两种都要截断。
    if not comment:
        return ""
    for sep in (":", "："):
        idx = comment.find(sep)
        if idx != -1:
            return comment[:idx].strip()
    return comment.strip()

def format_m_schema(schema_dict: dict) -> str:
    lines = []
    for name, t in schema_dict.get("tables", {}).items():
        comment = _clean_comment(t.get("comment", ""))
        enums = t.get("enums", {})
        cols = []
        for colname, col in t.get("columns", {}).items():
            coltype = col.get("type", "?")
            colcomment = _clean_comment(col.get("comment", ""))
            part = f"{colname}: {coltype}"
            if colcomment:
                part += f", {colcomment}"
            # 枚举取值:显式喂给 LLM,避免模型靠猜字面值(猜错查不到)
            if colname in enums and enums[colname]:
                part += ", 取值: " + ", ".join(enums[colname])
            cols.append("(" + part + ")")
        title = f"# Table: {name}" + (f", {comment}" if comment else "")
        lines.append(title)
        lines.append("[" + ", ".join(cols) + "]")
        # 外键:显式喂 join 关系,避免模型靠猜表关联(猜错查错)
        fks = t.get("fks", [])
        if fks:
            lines.append("外键: " + ", ".join(
                f"{fk['column']} → {fk['ref_table']}.{fk['ref_column']}" for fk in fks))
    return "\n".join(lines)

def build_prompt(question: str, schema_text: str, terms: str = "",
                 business_rules: str = "", examples: str = "", now: str = "",
                 dialect: str = "mysql") -> str:
    
    """拼完整提示词，全量注入（dialect 决定「按什么方言生成」+ 附该方言的写法提示）"""
    now = now or datetime.now().strftime("%Y-%m-%d %H:%M")
    dialect_name = _DIALECT_NAME.get(dialect, dialect)
    dialect_hint = _DIALECT_HINT.get(dialect, "")
    return f"""你是 Text2SQL 助手,把中文问题转成 {dialect_name} 只读 SQL。
{dialect_hint}

    【表结构】
    {schema_text}

    【业务术语】
    {terms or "(无)"}

    【业务口径】
    {business_rules or "(无)"}

    【参考示例】
    {examples or "(无)"}

    【输出要求】只输出 JSON,不要解释、不要 markdown 围栏,格式:
    {{"success": true, "sql": "...", "tables": ["..."], "chart-type": "...", "brief": "..."}}
    表名和列名只能来自上面的 schema,禁止编造;无法回答就输出
    {{"success": false, "brief": "无法回答"}}

   【当前时间】{now}

   【问题】{question}
  """
