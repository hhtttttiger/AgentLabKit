from __future__ import annotations

import re

from .base import BaseTokenizer, TokenizerResult
from .english import EnglishTokenizer

_MIXED_RUN_PATTERN = re.compile(r"[\u3400-\u9fff]+|[A-Za-z0-9]+")


class ChineseTokenizer(BaseTokenizer):
    script_name = "cjk"

    def __init__(self) -> None:
        self._english = EnglishTokenizer()

    def tokenize(self, text: str) -> TokenizerResult:
        tokens: list[str] = []
        for run in _MIXED_RUN_PATTERN.findall(text or ""):
            if re.search(r"[\u3400-\u9fff]", run):
                tokens.append(run)
                continue

            english_result = self._english.tokenize(run)
            tokens.extend(english_result.tokens)

        return TokenizerResult(
            tokens=tokens,
            detected_script=self.script_name,
            search_text=" ".join(tokens),
        )
