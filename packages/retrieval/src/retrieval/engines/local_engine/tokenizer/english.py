from __future__ import annotations

import re

from .base import BaseTokenizer, TokenizerResult

_LATIN_RUN_PATTERN = re.compile(r"[A-Za-z0-9]+")
_SPLIT_PATTERN = re.compile(r"[A-Z]?[a-z]+|[A-Z]+|[0-9]+")


def _split_latin_run(run: str) -> list[str]:
    if not run:
        return []

    if run.isdigit():
        return [run]

    if re.match(r"^[A-Z]{2,}[a-z].*$", run):
        prefix_chars: list[str] = []
        suffix_start = len(run)
        for index, char in enumerate(run):
            if char.isupper():
                prefix_chars.append(char)
                continue
            suffix_start = index
            break

        prefix = "".join(prefix_chars)
        suffix = run[suffix_start:]
        tokens = [prefix] if prefix else []
        if suffix:
            tokens.extend(_SPLIT_PATTERN.findall(suffix) or [suffix])
        return tokens

    return _SPLIT_PATTERN.findall(run) or [run]


class EnglishTokenizer(BaseTokenizer):
    script_name = "latin"

    def tokenize(self, text: str) -> TokenizerResult:
        tokens: list[str] = []
        for run in _LATIN_RUN_PATTERN.findall(text or ""):
            tokens.extend(token.lower() for token in _split_latin_run(run) if token)

        return TokenizerResult(
            tokens=tokens,
            detected_script=self.script_name,
            search_text=" ".join(tokens),
        )
