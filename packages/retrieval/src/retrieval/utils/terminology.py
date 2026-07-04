from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class GlossaryTerm:
    id: int
    category_id: int
    term: str
    synonyms: list[str]


@dataclass(slots=True, frozen=True)
class TerminologyMatch:
    start: int
    end: int
    canonical_term: str
    matched_text: str


@dataclass(slots=True, frozen=True)
class _Variant:
    normalized_text: str
    canonical_term: str


class TerminologyMatcher:
    def __init__(self, variants: list[_Variant]):
        self._variants = variants

    @classmethod
    def build(cls, terms: list[GlossaryTerm]) -> "TerminologyMatcher":
        variants: list[_Variant] = []
        seen: set[tuple[str, str]] = set()

        for term in terms:
            for variant in [term.term, *term.synonyms]:
                normalized = _normalize(variant)
                if not normalized:
                    continue

                key = (normalized, term.term)
                if key in seen:
                    continue

                seen.add(key)
                variants.append(_Variant(normalized_text=normalized, canonical_term=term.term))

        variants.sort(key=lambda item: (-len(item.normalized_text), item.normalized_text))
        return cls(variants)

    def match(self, raw_text: str) -> list[TerminologyMatch]:
        normalized_text = _normalize(raw_text)
        if not normalized_text:
            return []

        candidates: list[TerminologyMatch] = []
        for variant in self._variants:
            start_index = 0
            while True:
                found_at = normalized_text.find(variant.normalized_text, start_index)
                if found_at < 0:
                    break

                end_at = found_at + len(variant.normalized_text)
                if _has_token_boundaries(normalized_text, found_at, end_at):
                    candidates.append(
                        TerminologyMatch(
                            start=found_at,
                            end=end_at,
                            canonical_term=variant.canonical_term,
                            matched_text=raw_text[found_at:end_at],
                        )
                    )

                start_index = found_at + 1

        candidates.sort(key=lambda item: (item.start, -(item.end - item.start)))
        selected: list[TerminologyMatch] = []
        for candidate in candidates:
            if any(_ranges_overlap(candidate, current) for current in selected):
                continue
            selected.append(candidate)

        return selected

    def merge_tokens(
        self,
        raw_text: str,
        tokens: list[str],
        token_offsets: list[tuple[int, int]],
    ) -> list[str]:
        if not tokens or not token_offsets or len(tokens) != len(token_offsets):
            return list(tokens)

        matches = self.match(raw_text)
        if not matches:
            return list(tokens)

        merged: list[str] = []
        token_index = 0
        for match in matches:
            covered_indexes = [
                index
                for index, (start, end) in enumerate(token_offsets)
                if start >= match.start and end <= match.end
            ]
            if len(covered_indexes) <= 1:
                continue

            first_covered = covered_indexes[0]
            while token_index < first_covered:
                merged.append(tokens[token_index])
                token_index += 1

            merged.append(match.canonical_term)
            token_index = covered_indexes[-1] + 1

        while token_index < len(tokens):
            merged.append(tokens[token_index])
            token_index += 1

        return merged


def load_glossary_terms(payload: list[dict[str, Any]] | None) -> list[GlossaryTerm]:
    glossary_terms: list[GlossaryTerm] = []
    for item in payload or []:
        if not isinstance(item, dict):
            continue

        glossary_terms.append(
            GlossaryTerm(
                id=int(item.get("id", 0)),
                category_id=int(item.get("category_id", 0)),
                term=str(item.get("term", "")),
                synonyms=[str(value) for value in item.get("synonyms", []) if value is not None],
            )
        )

    return glossary_terms


def _normalize(value: str) -> str:
    return " ".join(value.lower().split())


def _has_token_boundaries(text: str, start: int, end: int) -> bool:
    left_ok = start == 0 or not text[start - 1].isalnum()
    right_ok = end == len(text) or not text[end].isalnum()
    return left_ok and right_ok


def _ranges_overlap(left: TerminologyMatch, right: TerminologyMatch) -> bool:
    return left.start < right.end and right.start < left.end
