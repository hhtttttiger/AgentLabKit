import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from retrieval.engines.local_engine.tokenizer import tokenize


class TestTokenizer(unittest.TestCase):
    def test_english_tokenizer_normalizes_to_lowercase_tokens(self):
        result = tokenize("Shipping Policy 2026")

        self.assertEqual(result.tokens, ["shipping", "policy", "2026"])
        self.assertEqual(result.search_text, "shipping policy 2026")
        self.assertEqual(result.detected_script, "latin")

    def test_cjk_tokenizer_handles_mixed_text(self):
        result = tokenize("使用RAGtechnology")

        self.assertIn("rag", [token.lower() for token in result.tokens])
        self.assertEqual(result.detected_script, "cjk")
        self.assertIn("使用", result.search_text)


if __name__ == "__main__":
    unittest.main()
