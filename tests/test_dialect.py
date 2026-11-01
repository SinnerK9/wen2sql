"""方言归一 ensure_dialect 的转译断言 + 一条端到端「MySQL 语法跑在 sqlite 引擎上」。"""
import re
import unittest

from app.executor.dialect import ensure_dialect
from app.executor.executor import execute


class TestEnsureDialect(unittest.TestCase):
    def test_date_format_to_strftime(self):
        out = ensure_dialect("SELECT DATE_FORMAT(order_date,'%Y-%m') FROM orders", "sqlite")
        self.assertIn("STRFTIME", out.upper())
        self.assertNotIn("DATE_FORMAT", out.upper())

    def test_concat_to_pipe(self):
        out = ensure_dialect("SELECT CONCAT(a, '-', b) FROM t", "sqlite")
        self.assertIn("||", out)
        self.assertNotIn("CONCAT", out.upper())

    def test_if_to_iif(self):
        out = ensure_dialect("SELECT IF(x > 0, 1, 0) FROM t", "sqlite")
        self.assertIn("IIF", out.upper())
        self.assertIsNone(re.search(r"\bIF\s*\(", out.upper()))

    def test_sqlite_pipe_is_not_rewritten_to_or(self):
        # 已经是目标方言的语法不能被 MySQL 解析器改写(|| → OR 会改语义)
        out = ensure_dialect("SELECT a || '-' || b FROM t", "sqlite")
        self.assertIn("||", out)
        self.assertNotIn(" OR ", out.upper())

    def test_mysql_target_keeps_mysql_syntax(self):
        out = ensure_dialect("SELECT DATE_FORMAT(order_date,'%Y-%m') FROM orders", "mysql")
        self.assertIn("DATE_FORMAT", out.upper())

    def test_unparseable_sql_returned_as_is(self):
        self.assertEqual(ensure_dialect("not sql at all (", "sqlite"), "not sql at all (")

    def test_mysql_syntax_runs_on_sqlite_engine(self):
        # 端到端:LLM 不听话写了 DATE_FORMAT,引擎是 sqlite,也必须查得出真数据
        result = execute(
            "SELECT DATE_FORMAT(order_date, '%Y-%m') AS m FROM orders WHERE id = 1",
            engine="sqlite",
        )
        self.assertEqual(result.rows[0][0], "2026-05")


if __name__ == "__main__":
    unittest.main()
