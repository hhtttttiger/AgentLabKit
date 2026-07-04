import unittest
from retrieval.engines.local_engine.document_loaders.loader_factory import LoaderFactory
from retrieval.engines.local_engine.splitter.splitter_factory import SplitterFactory
from retrieval.engines.local_engine.splitter.sentence_chunker import SentenceChunker
from retrieval.engines.local_engine.splitter.markdown.md_header_splitter import MDHeaderSplitter

class TestRagFactories(unittest.TestCase):

    def test_loader_factory_txt(self):
        loader = LoaderFactory.get_loader("txt")
        self.assertEqual(loader.__class__.__name__, "TxtLoader")

    def test_loader_factory_invalid(self):
        with self.assertRaises(ValueError):
            LoaderFactory.get_loader("invalid_type")

    def test_splitter_factory_default(self):
        factory = SplitterFactory(chunk_size=1000, chunk_overlap=100)
        splitter = factory.get_splitter("default", "txt")
        self.assertIsInstance(splitter, SentenceChunker)
        self.assertEqual(splitter.chunk_size, 1000)
        self.assertEqual(splitter.chunk_overlap, 100)

    def test_splitter_factory_md(self):
        factory = SplitterFactory(chunk_size=1000, chunk_overlap=100)
        splitter = factory.get_splitter("md", "md")
        self.assertIsInstance(splitter, MDHeaderSplitter)

    def test_splitter_factory_fallback(self):
        factory = SplitterFactory(chunk_size=1000, chunk_overlap=100)
        splitter = factory.get_splitter("unknown_splitter", "txt")
        # Should fallback to SentenceChunker (default)
        self.assertIsInstance(splitter, SentenceChunker)

if __name__ == "__main__":
    unittest.main()
