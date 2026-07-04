import unittest

from retrieval.engines.local_engine.retrievers.hybrid import HybridRetriever
from retrieval.model import Index, Segment, SegmentInfo


class TestHybridRetriever(unittest.TestCase):
    def setUp(self):
        self.retriever = HybridRetriever(SegmentInfo())
        self.segments = [
            Segment(
                id=1,
                text="Shipping policy allows returns within thirty days for unopened items.",
                metadata={"source": "shipping.md", "section": "returns"},
            ),
            Segment(
                id=2,
                text="Billing support can update invoices and resend payment receipts.",
                metadata={"source": "billing.md", "section": "invoices"},
            ),
            Segment(
                id=3,
                text="Store hours are from nine to six on weekdays.",
                metadata={"source": "store.md", "section": "hours"},
            ),
        ]
        self.indexes = [
            Index(segment_id=1, type="full_text", index="shipping policy returns unopened items", context=self.segments[0].text),
            Index(segment_id=2, type="full_text", index="billing invoices payment receipts", context=self.segments[1].text),
            Index(segment_id=3, type="embedding", index="store hours weekdays", context=self.segments[2].text),
        ]

    def test_search_returns_ranked_matches(self):
        self.retriever.sync_dataset(self.segments, self.indexes)

        results = self.retriever.search("shipping returns policy", top_k=2)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].id, "1")
        self.assertEqual(results[0].source, "shipping.md")
        self.assertGreater(results[0].score, 0.0)

    def test_search_respects_top_k_and_sorting(self):
        self.retriever.sync_dataset(self.segments, self.indexes)

        results = self.retriever.search("support receipts hours", top_k=2)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].id, "2")
        self.assertEqual(results[1].id, "3")

    def test_search_returns_empty_when_dataset_not_loaded(self):
        results = self.retriever.search("shipping", top_k=3)

        self.assertEqual(results, [])

    def test_search_ignores_blank_query(self):
        self.retriever.sync_dataset(self.segments, self.indexes)

        self.assertEqual(self.retriever.search("   ", top_k=3), [])


if __name__ == "__main__":
    unittest.main()
