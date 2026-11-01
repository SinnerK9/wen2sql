"""executor 执行层测试:stub 联调 + sqlite 真库(依赖 coffee_db/coffee.db)。"""
import sqlite3
import unittest
from pathlib import Path
from unittest import mock

from app.constants import MAX_ROWS
from app.executor.executor import Result, execute
from app.executor.sqlite_engine import fetch_sqlite
from app.executor.stub import fetch_stub


class TestExecute(unittest.TestCase):
    def test_stub_returns_result_contract(self):
        result = execute("SELECT anything", engine="stub")
        self.assertIsInstance(result, Result)
        self.assertEqual(result.columns, ["city", "total"])
        self.assertEqual(len(result.rows), 4)
        self.assertFalse(result.truncated)
        self.assertEqual(result.total, 4)

    def test_stub_ignores_sql(self):
        self.assertEqual(execute("DROP TABLE x", engine="stub").rows,
                         execute("SELECT 1", engine="stub").rows)

    def test_invalid_engine_raises(self):
        # sqlite 已是合法引擎,未知引擎才报错
        with self.assertRaises(ValueError):
            execute("SELECT 1", engine="oracle")

    def test_fetch_stub_shape(self):
        columns, rows, truncated, total = fetch_stub("SELECT 1")
        self.assertEqual(columns, ["city", "total"])
        self.assertEqual(total, len(rows))
        self.assertFalse(truncated)


class TestSqliteEngine(unittest.TestCase):
    """真库用例:coffee.db 实测 90 单 / 177 条明细,订单窗口 2026-05~07。"""

    def test_reads_real_data(self):
        result = execute("SELECT COUNT(*) FROM orders", engine="sqlite")
        self.assertEqual(result.rows[0][0], 90)

    def test_returns_result_contract(self):
        result = execute("SELECT id, city FROM store ORDER BY id", engine="sqlite")
        self.assertIsInstance(result, Result)
        self.assertEqual(result.columns, ["id", "city"])
        self.assertFalse(result.truncated)
        self.assertEqual(result.total, len(result.rows))
        # 行保持 tuple,不用 row_factory 改成 dict(摘要/图表都按 tuple 读)
        self.assertTrue(all(isinstance(row, tuple) for row in result.rows))

    def test_big_result_is_truncated_with_real_total(self):
        n = execute("SELECT COUNT(*) FROM order_item", engine="sqlite").rows[0][0]
        result = execute("SELECT a.id, b.id FROM order_item a, order_item b", engine="sqlite")
        self.assertTrue(result.truncated)
        self.assertEqual(len(result.rows), MAX_ROWS)
        self.assertEqual(result.total, n * n)

    def test_total_ignores_user_limit(self):
        # 截断后的 total 必须是「去掉 LIMIT」的真实行数,不是 LIMIT 的值
        n = execute("SELECT COUNT(*) FROM order_item", engine="sqlite").rows[0][0]
        result = execute(
            "SELECT a.id, b.id FROM order_item a, order_item b ORDER BY a.id LIMIT 5000",
            engine="sqlite",
        )
        self.assertTrue(result.truncated)
        self.assertEqual(len(result.rows), MAX_ROWS)
        self.assertEqual(result.total, n * n)

    def test_readonly_connection_blocks_writes(self):
        # 校验器被绕过时的第二道防线:连接层只读
        with self.assertRaises(sqlite3.Error):
            execute("DELETE FROM orders", engine="sqlite")
        self.assertEqual(execute("SELECT COUNT(*) FROM orders", engine="sqlite").rows[0][0], 90)

    def test_timeout_interrupts_runaway_query(self):
        # 无终止递归 CTE:SQLite 没有服务端超时,只能靠 progress_handler 主动中断
        with mock.patch("app.executor.sqlite_engine.EXEC_TIMEOUT", 0.2):
            with self.assertRaises(TimeoutError):
                fetch_sqlite("WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL "
                             "SELECT x + 1 FROM c) SELECT COUNT(*) FROM c")

    def test_missing_db_gives_clear_error(self):
        with mock.patch("app.config.SQLITE_DB", Path("no_such_coffee.db")):
            with self.assertRaises(FileNotFoundError):
                execute("SELECT 1", engine="sqlite")


if __name__ == "__main__":
    unittest.main()
