import pymysql
from .extract_enums import extract_enums_from_comment
from .models import Table, Schema, ForeignKey, Column

def extract_from_mysql(host: str, port: int, user: str, password: str, db: str) -> Schema:
    conn = pymysql.connect(host=host, port=port, user=user, password=password, database=db, charset="utf8mb4")
    try:
        with conn.cursor() as cur:
            schema = Schema()
            # 真库抽取表名＋注释
            cur.execute("SELECT TABLE_NAME, TABLE_COMMENT FROM information_schema.TABLES "
                        "WHERE TABLE_SCHEMA=%s ORDER BY TABLE_NAME", (db,))
            tables = {name: Table(comment=comment or "") for name, comment in cur.fetchall()}

            # 抽取列信息
            cur.execute("SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, COLUMN_COMMENT "
                        "FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s "
                        "ORDER BY TABLE_NAME, ORDINAL_POSITION", (db,))
            for tabname, colname, coltype, colcomment in cur.fetchall():
                t = tables.get(tabname) # 防御性编程
                if t is None:
                    continue
                colcomment = colcomment or "" # 实际不一定存在colcomment，留其为None而不是""可能导致keyerror
                t.columns[colname] = Column(type=coltype, comment=colcomment)
                if coltype.lower().startswith("enum("):
                    # 利用find/rfind取出enum中的对
                    inner = coltype[coltype.find("(") + 1: coltype.rfind(")")]
                    # 将enum对用,分隔开并去除引号
                    t.enums[colname] = [v.strip().strip("'\"") for v in inner.split(",")]
                # 注释中enums
                else:
                    vals = extract_enums_from_comment(colcomment)
                    if vals:
                        t.enums[colname] = vals
            # 查询外键信息，REFERENCED_TABLE_NAME IS NOT NULL 指示外键
            cur.execute(
                "SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME "
                "FROM information_schema.KEY_COLUMN_USAGE "
                "WHERE TABLE_SCHEMA=%s AND REFERENCED_TABLE_NAME IS NOT NULL", (db,))
            for tablename, columnname, rtabname, rcolname in cur.fetchall():
                t = tables.get(tablename)
                if t is not None:
                    t.fks.append(ForeignKey(column=columnname, ref_table=rtabname, ref_column=rcolname))
            schema.tables = tables
            return schema
    finally:
        conn.close()
