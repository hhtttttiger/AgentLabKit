from __future__ import annotations

from loguru import logger

from retrieval.engines.local_engine.tokenizer import tokenize

from .base_step import PipelineStep


class TokenizerStep(PipelineStep):
    def execute(self):
        if not self.context.success or not self.context.text_list:
            return

        try:
            for segment in self.context.text_list:
                result = tokenize(segment.text)
                segment.word_segmentation = result.search_text
                segment.keywords = result.tokens
                segment.detected_script = result.detected_script
        except Exception as exc:
            self.context.success = False
            self.context.segment_info.errorMessage = str(exc)
            logger.exception(f"Tokenizer step failed: {exc}")
