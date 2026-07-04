from __future__ import annotations

from retrieval.utils.terminology import TerminologyMatcher

from .base_step import PipelineStep


class TerminologyStep(PipelineStep):
    def execute(self):
        matcher = self.context.terminology_matcher
        if not self.context.success or matcher is None or not self.context.text_list:
            return

        for segment in self.context.text_list:
            if not segment.keywords:
                continue

            token_offsets = _build_token_offsets(segment.text, segment.keywords)
            if len(token_offsets) != len(segment.keywords):
                continue

            merged_keywords = matcher.merge_tokens(
                raw_text=segment.text,
                tokens=segment.keywords,
                token_offsets=token_offsets,
            )
            segment.keywords = merged_keywords
            segment.word_segmentation = " ".join(merged_keywords)


def _build_token_offsets(raw_text: str, tokens: list[str]) -> list[tuple[int, int]]:
    offsets: list[tuple[int, int]] = []
    lowered_text = raw_text.lower()
    cursor = 0

    for token in tokens:
        lowered_token = token.lower()
        start = lowered_text.find(lowered_token, cursor)
        if start < 0:
            return []

        end = start + len(token)
        offsets.append((start, end))
        cursor = end

    return offsets
