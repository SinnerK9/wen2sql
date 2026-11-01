"""解析MySQL DDL - schema"""
import sqlglot
from sqlglot import expressions as exp

from .models import Table, Schema, ForeignKey, Column
from .extract_enums import extract_enums_from_comment

def _name_of(node) -> str:
    if node is None:
        return ""
    if isinstance(node, exp.Identifier):
        return node.this
    if isinstance(node, exp.Table):
        return _name_of(node.this)
    if isinstance(node, exp.Schema):
        return _name_of(node.this)
    if hasattr(node, "name") and node.name:
        return node.name

def _Ident(nodes) -> list:
    outlist = []
    for node in (nodes or []):
        if isinstance(node,exp.Identifier):
            outlist.append(node.this)
        else:
            n = _name_of(node)
            if n:
                outlist.append(n)
    return outlist

def _table_comment(stmt: exp.Create) -> str:
    properties = stmt.args.get("properties") # 所有的Table级附加信息都在args["properties"]下
    if properties:
        for prop in properties.expressions:
            # 
            if isinstance(prop, exp.SchemaCommentProperty) and prop.this: # 是表注释类且有值
                return prop.this.this or "" # prop -> literal -> 真正的注释
    return ""

def _table_name(stmt: exp.Create) -> str:
    node = stmt.this.this # Create -> schema -> table
    return _name_of(node)

# col comment文本：ColumnDef -> constraints -> kind ->(是columnstraint) -> literal -> 字符串
def _col_comment(ColDef: exp.ColumnDef):
    # 对于无约束的列，get返回None会导致崩溃，增加or[]防御性编程
    for Cons in (ColDef.args.get("constraints") or []):
        kind = Cons.args.get("kind")
        if isinstance(kind, exp.CommentColumnConstraint):
            return kind.this.this or "" # kind -> literal -> 真正的列注释
    return ""
# 实测发现ColDef.find(exp.ColumnConstraint)会直接返回None，必须从ColumnDef开始

# 将解析出来的AST节点转化为对象
def _parse_create(stmt: exp.Create) -> Table:
    table = Table(_table_comment(stmt))

    # 表的每一列：name + type + comment
    for ColDef in stmt.find_all(exp.ColumnDef):
        colname = ColDef.this.this
        colkind = ColDef.args.get("kind")
        if colkind:
            coltype = colkind.sql()
        else:
            coltype = "?"
        table.columns[colname] = Column(type=coltype, comment=_col_comment(ColDef))
        # 部分列的类型可能是ENUM，该部分存在table的enums[列名]
        if colkind and colkind.is_type(exp.DataType.Type.ENUM):
            # enum类下所有Literal取this即为枚举内容
            table.enums[colname] = [lit.this for lit in colkind.find_all(exp.Literal)]
        # 增加对类型非enums但在注释里进行枚举的库的支持
        else:
            vals = extract_enums_from_comment(table.columns[colname].comment)
            if vals:
                table.enums[colname] = vals

    # 外键处理：考虑普通外键和库名外键的区别
    for fk in stmt.find_all(exp.ForeignKey):
        cols = _Ident(fk.expressions) # 将其中的多个identifiers变为涉及列表
        refer = fk.args.get("reference")
        if not refer:
            continue
        rt = refer.this
        # 库名外键，reference.this是schema，引用列在schema.expressions
        if isinstance(rt,exp.Schema):
            reftable = _name_of(rt.this)
            refcols = _Ident(rt.expressions)
        # 一般外键：reference.this是table，引用列在reference.expressions，一系列identifiers
        else:
            reftable = _name_of(rt)
            refcols = _Ident(refer.expressions)
        for c, rc in zip(cols, refcols):
            table.fks.append(ForeignKey(column=c, ref_table=reftable, ref_column=rc))

    return table

# 解析 MySQL DDL 文本为 Schema。
def parse_ddl(text: str) -> Schema:
    schema = Schema()
    for stmt in sqlglot.parse(text, read="mysql"):
        # 只解析建表语句
        if not (isinstance(stmt, exp.Create) and isinstance(stmt.this, exp.Schema)):
            continue
        name = _table_name(stmt)
        if name:
            schema.tables[name] = _parse_create(stmt)
    return schema
