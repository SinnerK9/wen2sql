"""注释枚举提取测试。"""
import unittest

from app.schema.extract_enums import extract_enums_from_comment


class TestExtractEnumsFromComment(unittest.TestCase):
    def test_chinese_fullwidth_colon(self):
        self.assertEqual(
            extract_enums_from_comment("会员等级：普通, 银卡, 金卡, 黑金"),
            ["普通", "银卡", "金卡", "黑金"])

    def test_english_halfwidth_colon(self):
        self.assertEqual(
            extract_enums_from_comment("状态: DRAFT, SIGNED, ARCHIVED"),
            ["DRAFT", "SIGNED", "ARCHIVED"])

    def test_chinese_comma_separators(self):
        self.assertEqual(
            extract_enums_from_comment("支付方式（微信，支付宝，现金）"),
            ["微信", "支付宝", "现金"])

    def test_single_value_not_enum(self):
        self.assertEqual(extract_enums_from_comment("状态: 已完成"), [])

    def test_space_separated_words_not_enum(self):
        self.assertEqual(
            extract_enums_from_comment("备注（使用 HTTP API 时的注意事项）"), [])

    def test_empty_comment(self):
        self.assertEqual(extract_enums_from_comment(""), [])
        self.assertEqual(extract_enums_from_comment(None), [])


if __name__ == "__main__":
    unittest.main()
