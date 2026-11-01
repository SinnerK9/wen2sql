"""ddl_parser(MySQL DDL → Schema)解析测试。"""
import unittest

from app.schema.ddl_parser import parse_ddl

CATEGORY_DDL = """
CREATE TABLE `category` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '品类ID',
  `name` varchar(100) NOT NULL COMMENT '品类名称',
  `parent_id` bigint DEFAULT NULL COMMENT '父品类ID',
  PRIMARY KEY (`id`),
  CONSTRAINT `category_ibfk_1` FOREIGN KEY (`parent_id`)
    REFERENCES `category` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='品类表';
"""

PRODUCT_DDL = """
CREATE TABLE `product` (
  `id` bigint NOT NULL COMMENT '商品ID',
  `category_id` bigint NOT NULL COMMENT '所属品类ID',
  `status` varchar(20) COMMENT '状态：DRAFT, SIGNED, ARCHIVED',
  FOREIGN KEY (`category_id`) REFERENCES `mydb`.`category` (`id`)
) COMMENT='商品表';
"""


class TestParseDDL(unittest.TestCase):
    def test_table_name_and_comment(self):
        schema = parse_ddl(CATEGORY_DDL)
        self.assertIn("category", schema.tables)
        self.assertEqual(schema.tables["category"].comment, "品类表")

    def test_columns(self):
        table = parse_ddl(CATEGORY_DDL).tables["category"]
        self.assertEqual(set(table.columns), {"id", "name", "parent_id"})
        self.assertEqual(table.columns["id"].comment, "品类ID")
        self.assertEqual(table.columns["parent_id"].type.upper(), "BIGINT")

    def test_self_reference_fk(self):
        table = parse_ddl(CATEGORY_DDL).tables["category"]
        self.assertEqual(len(table.fks), 1)
        fk = table.fks[0]
        self.assertEqual(fk.column, "parent_id")
        self.assertEqual(fk.ref_table, "category")
        self.assertEqual(fk.ref_column, "id")

    def test_qualified_db_fk(self):
        table = parse_ddl(PRODUCT_DDL).tables["product"]
        self.assertEqual(len(table.fks), 1)
        fk = table.fks[0]
        self.assertEqual(fk.column, "category_id")
        self.assertEqual(fk.ref_table, "category")
        self.assertEqual(fk.ref_column, "id")

    def test_enum_from_comment(self):
        table = parse_ddl(PRODUCT_DDL).tables["product"]
        self.assertEqual(table.enums["status"], ["DRAFT", "SIGNED", "ARCHIVED"])

    def test_non_create_statements_skipped(self):
        schema = parse_ddl("CREATE DATABASE x; " + CATEGORY_DDL)
        self.assertEqual(set(schema.tables), {"category"})

    def test_empty_input(self):
        schema = parse_ddl("")
        self.assertEqual(schema.tables, {})


if __name__ == "__main__":
    unittest.main()
