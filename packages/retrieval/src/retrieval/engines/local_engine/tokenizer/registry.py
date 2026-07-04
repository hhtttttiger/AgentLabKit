from __future__ import annotations

import re

from .base import BaseTokenizer, TokenizerResult
from .chinese import ChineseTokenizer
from .english import EnglishTokenizer

_CJK_PATTERN = re.compile(r"[\u3400-\u9fff]")

_LATIN_TOKENIZER = EnglishTokenizer()
_CJK_TOKENIZER = ChineseTokenizer()


def resolve_tokenizer(text: str) -> BaseTokenizer:
    if _CJK_PATTERN.search(text or ""):
        return _CJK_TOKENIZER
    return _LATIN_TOKENIZER


def tokenize(text: str) -> TokenizerResult:
    return resolve_tokenizer(text).tokenize(text)
