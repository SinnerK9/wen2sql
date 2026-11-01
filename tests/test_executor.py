"""executor 执行层测试(stub 路径,不连真库)。"""
import unittest

from app.executor.executor import Result, execute
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
        with self.assertRaises(ValueError):
            execute("SELECT 1", engine="sqlite")

    def test_fetch_stub_shape(self):
        columns, rows, truncated, total = fetch_stub("SELECT 1")
        self.assertEqual(columns, ["city", "total"])
        self.assertEqual(total, len(rows))
        self.assertFalse(truncated)


if __name__ == "__main__":
    unittest.main()
