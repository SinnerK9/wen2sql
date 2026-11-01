"""truncate(COUNT 真总数)与 with_timeout(超时 hint)测试。"""
import unittest

from app.executor.truncate import truncate, with_timeout


class TestTruncate(unittest.TestCase):
    def test_top_level_limit_removed(self):
        sql = "SELECT * FROM orders LIMIT 1000"
        self.assertEqual(truncate(sql),
                         "SELECT COUNT(*) FROM (SELECT * FROM orders) AS subq")

    def test_limit_and_order_removed(self):
        sql = "SELECT * FROM orders ORDER BY total_amount DESC LIMIT 1000"
        out = truncate(sql)
        self.assertNotIn("ORDER BY", out)
        self.assertNotIn("LIMIT", out)

    def test_subquery_limit_kept(self):
        sql = "SELECT * FROM (SELECT * FROM orders LIMIT 5) s"
        out = truncate(sql)
        self.assertIn("LIMIT 5", out)

    def test_aggregate_wrapped(self):
        sql = "SELECT city, SUM(total_amount) FROM orders GROUP BY city"
        self.assertEqual(truncate(sql),
                         f"SELECT COUNT(*) FROM ({sql}) AS subq")

    def test_union_not_stripped(self):
        sql = "SELECT id FROM orders UNION SELECT id FROM store"
        self.assertEqual(truncate(sql),
                         f"SELECT COUNT(*) FROM ({sql}) AS subq")

    def test_unparseable_falls_back_raw(self):
        sql = "not sql at all ("
        self.assertEqual(truncate(sql),
                         f"SELECT COUNT(*) FROM ({sql}) AS subq")


class TestWithTimeout(unittest.TestCase):
    def test_select_gets_hint(self):
        out = with_timeout("SELECT 1", 10000)
        self.assertIn("MAX_EXECUTION_TIME(10000)", out)

    def test_non_select_returned_unchanged(self):
        out = with_timeout("INSERT INTO t VALUES (1)", 10000)
        self.assertNotIn("MAX_EXECUTION_TIME", out)

    def test_unparseable_returned_unchanged(self):
        out = with_timeout("garbage ((", 10000)
        self.assertEqual(out, "garbage ((")


if __name__ == "__main__":
    unittest.main()
