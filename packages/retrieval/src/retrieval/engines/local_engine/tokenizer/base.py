from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class TokenizerResult:
    tokens: list[str]
    detected_script: str
    search_text: str


class BaseTokenizer(ABC):
    script_name = "unknown"

    @abstractmethod
    def tokenize(self, text: str) -> TokenizerResult:
        raise NotImplementedError
