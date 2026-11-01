"""LLM JSON 容错解析测试。"""
import unittest

from app.llm.json_parse import extract_json


class TestExtractJson(unittest.TestCase):
    def test_clean_json(self):
        self.assertEqual(extract_json('{"a": 1}'), {"a": 1})

    def test_markdown_fence(self):
        self.assertEqual(extract_json('```json\n{"a": 1}\n```'), {"a": 1})

    def test_markdown_fence_without_lang(self):
        self.assertEqual(extract_json('```\n{"a": 1}\n```'), {"a": 1})

    def test_surrounding_text(self):
        self.assertEqual(extract_json('以下是结果 {"a": 1} 完毕'), {"a": 1})

    def test_nested_braces(self):
        self.assertEqual(extract_json('{"a": {"b": [1, 2, 3]}}'),
                         {"a": {"b": [1, 2, 3]}})

    def test_braces_inside_string(self):
        self.assertEqual(extract_json('{"s": "a {b} c", "n": 2}'),
                         {"s": "a {b} c", "n": 2})

    def test_trailing_garbage_after_json(self):
        self.assertEqual(extract_json('```json\n{"a": 1}\n``` 后面还有废话'),
                         {"a": 1})

    def test_invalid_json_returns_none(self):
        self.assertIsNone(extract_json('{"a": 1'))

    def test_no_brace_returns_none(self):
        self.assertIsNone(extract_json("没有任何花括号"))

    def test_empty_input_returns_none(self):
        self.assertIsNone(extract_json(""))
        self.assertIsNone(extract_json(None))


if __name__ == "__main__":
    unittest.main()
