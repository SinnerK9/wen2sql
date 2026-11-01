"""validator 7 项校验的边界测试。运行:python -m unittest discover -s tests"""
import unittest

from app.validate.validator import validate
from app.constants import DEFAULT_LIMIT

TABLES = {
    "orders": {"columns": {"id": {}, "total_amount": {}, "status": {}, "store_id": {}, "order_date": {}}},
    "store": {"columns": {"id": {}, "city": {}, "name": {}}},
}


class TestReadOnly(unittest.TestCase):
    def test_delete_blocked(self):
        ok, errors, _ = validate("DELETE FROM orders", TABLES)
        self.assertFalse(ok)
        self.assertTrue(any("只允许 SELECT" in e for e in errors))

    def test_update_blocked(self):
        ok, errors, _ = validate("UPDATE orders SET status='x'", TABLES)
        self.assertFalse(ok)

    def test_select_allowed(self):
        ok, errors, _ = validate("SELECT * FROM orders", TABLES)
        self.assertTrue(ok)

    def test_union_allowed(self):
        ok, _, _ = validate("SELECT id FROM orders UNION SELECT id FROM store", TABLES)
        self.assertTrue(ok)

    def test_with_select_allowed(self):
        ok, _, _ = validate("WITH cte AS (SELECT id FROM orders) SELECT * FROM cte", TABLES)
        self.assertTrue(ok)


class TestSingleStatement(unittest.TestCase):
    def test_multi_statement_blocked(self):
        ok, errors, _ = validate("SELECT 1; SELECT 2", TABLES)
        self.assertFalse(ok)
        self.assertTrue(any("单语句" in e for e in errors))


class TestTableWhitelist(unittest.TestCase):
    def test_fake_table_blocked(self):
        ok, errors, _ = validate("SELECT * FROM fake_table", TABLES)
        self.assertFalse(ok)
        self.assertTrue(any("未授权表" in e for e in errors))

    def test_cte_name_not_flagged(self):
        ok, errors, _ = validate("WITH cte AS (SELECT id FROM orders) SELECT * FROM cte", TABLES)
        self.assertTrue(ok, errors)

    def test_qualified_schema_other_than_expected(self):
        ok, errors, _ = validate("SELECT * FROM other_db.orders", TABLES)
        # EXPECTED_SCHEMA 为空时不校验库名
        self.assertTrue(ok, errors)


class TestJoinCount(unittest.TestCase):
    def test_join_over_limit_blocked(self):
        many = {f"t{i}": {"columns": {}} for i in range(1, 10)}
        ok, errors, _ = validate(
            "SELECT * FROM " + ",".join(f"t{i}" for i in range(1, 10)), many)
        self.assertFalse(ok)
        self.assertTrue(any("联表数超过上限" in e for e in errors))


class TestDangerousFuncs(unittest.TestCase):
    def test_sleep_blocked(self):
        ok, errors, _ = validate("SELECT SLEEP(1)", TABLES)
        self.assertFalse(ok)
        self.assertTrue(any("危险函数" in e for e in errors))

    def test_benchmark_blocked(self):
        ok, errors, _ = validate("SELECT BENCHMARK(1000000, SHA1('x'))", TABLES)
        self.assertFalse(ok)

    def test_load_file_blocked(self):
        ok, errors, _ = validate("SELECT LOAD_FILE('/etc/passwd')", TABLES)
        self.assertFalse(ok)


class TestColumnCheck(unittest.TestCase):
    def test_wrong_column_blocked(self):
        ok, errors, _ = validate("SELECT bad_col FROM orders", TABLES)
        self.assertFalse(ok)
        self.assertTrue(any("不存在" in e for e in errors))

    def test_wrong_alias_column_blocked(self):
        ok, errors, _ = validate("SELECT o.bad FROM orders o", TABLES)
        self.assertFalse(ok)
        self.assertTrue(any("列 bad 在表 orders" in e for e in errors))

    def test_good_alias_column_allowed(self):
        ok, errors, _ = validate("SELECT o.id FROM orders o", TABLES)
        self.assertTrue(ok, errors)

    def test_join_good_columns_allowed(self):
        sql = "SELECT s.city, o.total_amount FROM orders o JOIN store s ON o.store_id = s.id"
        ok, errors, _ = validate(sql, TABLES)
        self.assertTrue(ok, errors)


class TestLimitInjection(unittest.TestCase):
    def test_unbounded_select_gets_limit(self):
        ok, _, final = validate("SELECT * FROM orders", TABLES)
        self.assertTrue(ok)
        self.assertIn(f"LIMIT {DEFAULT_LIMIT}", final)

    def test_aggregate_not_limited(self):
        sql = ("SELECT s.city, SUM(o.total_amount) AS total "
               "FROM orders o JOIN store s ON o.store_id = s.id "
               "GROUP BY s.city")
        ok, errors, final = validate(sql, TABLES)
        self.assertTrue(ok, errors)
        self.assertNotIn("LIMIT", final)

    def test_distinct_not_limited(self):
        ok, _, final = validate("SELECT DISTINCT city FROM store", TABLES)
        self.assertTrue(ok)
        self.assertNotIn("LIMIT", final)

    def test_existing_small_limit_kept(self):
        ok, _, final = validate("SELECT * FROM orders LIMIT 5", TABLES)
        self.assertTrue(ok)
        self.assertIn("LIMIT 5", final)

    def test_union_gets_limit(self):
        ok, _, final = validate(
            "SELECT id FROM orders UNION SELECT id FROM store", TABLES)
        self.assertTrue(ok)
        self.assertIn(f"LIMIT {DEFAULT_LIMIT}", final)


class TestDialect(unittest.TestCase):
    """方言参数化:SQLite 的 || 拼接不能被 MySQL 解析器读成 OR(语义会变)。"""

    def test_sqlite_dialect_injects_limit(self):
        ok, errors, final = validate("SELECT * FROM orders", TABLES, dialect="sqlite")
        self.assertTrue(ok, errors)
        self.assertIn(f"LIMIT {DEFAULT_LIMIT}", final)

    def test_sqlite_concat_kept_as_pipe(self):
        ok, errors, final = validate(
            "SELECT city || '-' || name AS label FROM store", TABLES, dialect="sqlite")
        self.assertTrue(ok, errors)
        self.assertIn("||", final)
        self.assertNotIn(" OR ", final.upper())

    def test_default_dialect_is_mysql(self):
        ok, _, final = validate("SELECT CONCAT(city, name) AS label FROM store", TABLES)
        self.assertTrue(ok)
        self.assertIn("CONCAT", final.upper())


if __name__ == "__main__":
    unittest.main()
