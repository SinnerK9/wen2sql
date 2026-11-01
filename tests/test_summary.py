"""summary 摘要生成测试(四种数据形态)。"""
import unittest

from app.summary import summarize

ROWS = [("上海", 665.0), ("北京", 532.0), ("深圳", 398.0), ("杭州", 275.0)]


class TestSummarize(unittest.TestCase):
    def test_text_plus_number(self):
        out = summarize(["city", "total"], ROWS)
        self.assertIn("共 4 个城市有订单", out)
        self.assertIn("合计 ¥1,870.00", out)
        self.assertIn("最高是 上海 ¥665.00", out)
        self.assertIn("占 35.6%", out)

    def test_number_only(self):
        self.assertEqual(summarize(["total"], [(100.0,), (50.0,)]),
                         "合计 ¥150.00")

    def test_text_only(self):
        out = summarize(["status"], [("已完成",), ("已完成",), ("已取消",)])
        self.assertIn("已完成(2次)", out)
        self.assertIn("已取消(1次)", out)

    def test_empty_result(self):
        self.assertEqual(summarize([], []), "无数据")
        self.assertEqual(summarize(["city", "total"], []), "无数据")

    def test_unknown_columns_fall_back_to_raw_name(self):
        out = summarize(["foo", "bar"], [("a", 1.0), ("b", 2.0)])
        self.assertIn("2 个foo有订单", out)


if __name__ == "__main__":
    unittest.main()
