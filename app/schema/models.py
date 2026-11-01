"""schema.json数据模型"""
from dataclasses import dataclass, field

@dataclass
class Column:
    type:str
    comment:str = ""

@dataclass
class ForeignKey:
    column: str
    ref_table: str
    ref_column: str

@dataclass
class Table:
    comment: str = ""
    columns: dict = field(default_factory=dict)
    enums: dict = field(default_factory=dict)
    fks: list = field(default_factory=list)

@dataclass
class Schema:
    tables: dict = field(default_factory=dict)

    def to_dict(self,source: str = "") -> dict:
        return{
            "tables":{
                name:{
                    "comment": t.comment,
                    "columns": {c: {"type": col.type, "comment": col.comment} for c, col in t.columns.items()},
                    "enums": {k: list(v) for k, v in t.enums.items()},
                    "fks": [{"column": fk.column, "ref_table": fk.ref_table, "ref_column": fk.ref_column} for fk in t.fks]
                }for name, t in self.tables.items()
            },
            "_meta": {"source": source},
        }