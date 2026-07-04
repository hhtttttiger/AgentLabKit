import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from retrieval.engines.local_engine.context import PipelineContext
from retrieval.engines.local_engine.engine import LocalRagEngine
from retrieval.engines.local_engine.steps.terminology_step import TerminologyStep
from retrieval.model import Segment, SegmentInfo, SegmentSetting
from retrieval.utils.terminology import GlossaryTerm, TerminologyMatcher


class TestTerminologyMatcher(unittest.TestCase):
    def test_matcher_prefers_longest_term_when_ranges_overlap(self):
        matcher = TerminologyMatcher.build(
            [
                GlossaryTerm(
                    id=1,
                    category_id=10,
                    term="Retrieval Augmented Generation",
                    synonyms=[],
                ),
                GlossaryTerm(id=2, category_id=10, term="Generation", synonyms=[]),
            ]
        )

        matches = matcher.match("Retrieval Augmented Generation pipeline")

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].matched_text, "Retrieval Augmented Generation")

    def test_merge_tokens_replaces_split_tokens_with_canonical_term(self):
        matcher = TerminologyMatcher.build(
            [
                GlossaryTerm(
                    id=1,
                    category_id=10,
                    term="Shipping Policy",
                    synonyms=["Delivery Policy"],
                )
            ]
        )

        merged = matcher.merge_tokens(
            raw_text="The shipping policy is strict",
            tokens=["the", "shipping", "policy", "is", "strict"],
            token_offsets=[(0, 3), (4, 12), (13, 19), (20, 22), (23, 29)],
        )

        self.assertEqual(merged, ["the", "Shipping Policy", "is", "strict"])

    def test_terminology_step_merges_segment_keywords_and_word_segmentation(self):
        context = PipelineContext()
        context.text_list = [
            Segment(
                id=1,
                text="The shipping policy is strict",
                keywords=["the", "shipping", "policy", "is", "strict"],
                word_segmentation="the shipping policy is strict",
            )
        ]
        context.terminology_matcher = TerminologyMatcher.build(
            [
                GlossaryTerm(
                    id=1,
                    category_id=10,
                    term="Shipping Policy",
                    synonyms=["Delivery Policy"],
                )
            ]
        )

        TerminologyStep(context).execute()

        self.assertEqual(context.text_list[0].keywords, ["the", "Shipping Policy", "is", "strict"])
        self.assertEqual(context.text_list[0].word_segmentation, "the Shipping Policy is strict")

    def test_local_rag_engine_merges_glossary_terms_before_full_text_indexing(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as handle:
            handle.write("The shipping policy is strict.")
            file_path = handle.name

        try:
            engine = LocalRagEngine(
                file_path,
                segment_info=SegmentInfo(
                    setting=SegmentSetting(
                        indexes=["full_text"],
                        provider_config={
                            "terminology_terms": [
                                {
                                    "id": 1,
                                    "category_id": 10,
                                    "term": "Shipping Policy",
                                    "synonyms": ["Delivery Policy"],
                                }
                            ]
                        },
                    )
                ),
            )

            success = engine.activate()

            self.assertTrue(success)
            full_text_indexes = [index for index in engine.context.index_result if index.type == "full_text"]
            self.assertTrue(full_text_indexes)
            self.assertIn("Shipping Policy", full_text_indexes[0].metadata["keywords"])
            self.assertNotIn("shipping", full_text_indexes[0].metadata["keywords"])
            self.assertNotIn("policy", full_text_indexes[0].metadata["keywords"])
        finally:
            os.remove(file_path)


if __name__ == "__main__":
    unittest.main()
