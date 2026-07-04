import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from retrieval.engine import RagEngine
from retrieval.model import SegmentInfo, SegmentSetting, LoaderConfig, SplitterConfig, GraphConfig, GraphStorageConfig

from retrieval.engines.local_engine.engine import LocalRagEngine


class TestRagEngine(unittest.TestCase):

    def setUp(self):
        self.test_file = "test_doc_engine.txt"
        with open(self.test_file, "w", encoding="utf-8") as f:
            f.write("# Title\n\nThis is a test paragraph.\n\n## Subtitle\n\nAnother paragraph.")

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_rag_engine_init_default(self):
        file_path = os.path.abspath(self.test_file)
        engine = RagEngine(file_path)

        # Facade checks
        self.assertIsInstance(engine.engine, LocalRagEngine)

        # Local Engine context checks
        local_engine = engine.engine
        self.assertIsNotNone(local_engine.context)
        self.assertIsNotNone(local_engine.context.segment_info)
        self.assertIsNotNone(local_engine.context.segment_info.status)
        self.assertIsNotNone(local_engine.context.segment_info.setting)

        # Verify defaults
        self.assertEqual(local_engine.context.segment_info.setting.mode, "default")
        self.assertEqual(local_engine.context.segment_info.setting.loader.name, "")
        self.assertEqual(local_engine.context.segment_info.setting.splitter.name, "default")
        self.assertEqual(local_engine.context.file_info.file_path, file_path)
        self.assertEqual(local_engine.context.file_info.file_name, os.path.basename(self.test_file))

    def test_rag_engine_init_custom(self):
        file_path = os.path.abspath(self.test_file)
        custom_info = SegmentInfo(
            setting=SegmentSetting(
                maxLength=2048,
                overlap=200,
                indexes=["embedding", "full_text"],
                loader=LoaderConfig(name="custom_loader"),
                splitter=SplitterConfig(name="recursive")
            )
        )
        engine = RagEngine(file_path, segment_info=custom_info)

        self.assertIsInstance(engine.engine, LocalRagEngine)
        local_engine = engine.engine

        self.assertEqual(local_engine.context.segment_info.setting.maxLength, 2048)
        self.assertEqual(local_engine.context.segment_info.setting.overlap, 200)
        self.assertEqual(local_engine.context.segment_info.setting.indexes, ["embedding", "full_text"])
        self.assertEqual(local_engine.context.segment_info.setting.loader.name, "custom_loader")
        self.assertEqual(local_engine.context.segment_info.setting.splitter.name, "recursive")

    def test_rag_engine_execution(self):
        file_path = os.path.abspath(self.test_file)
        engine = RagEngine(file_path)
        success = engine.activate()

        self.assertTrue(success)

        local_engine = engine.engine
        self.assertTrue(len(local_engine.context.text_list) > 0)
        self.assertTrue(len(local_engine.context.index_result) > 0)

        # Verify status updates
        self.assertEqual(local_engine.context.segment_info.status.loader.status, 1)
        self.assertEqual(local_engine.context.segment_info.status.splitter.status, 1)
        # Check index status
        self.assertTrue(len(local_engine.context.segment_info.status.indexes) > 0)
        for idx in local_engine.context.segment_info.status.indexes:
            self.assertEqual(idx.status, 1)

    def test_rag_engine_search_local(self):
        file_path = os.path.abspath(self.test_file)
        engine = RagEngine(file_path)

        # 未 activate 前，尚未加载可检索数据
        results = engine.search("test")
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 0)

        success = engine.activate()
        self.assertTrue(success)

        results = engine.search("test paragraph")
        self.assertGreater(len(results), 0)
        self.assertIn("test paragraph", results[0].text.lower())

    def test_engine_activate_populates_embedding_and_full_text_indexes(self):
        file_path = os.path.abspath(self.test_file)
        engine = RagEngine(
            file_path,
            segment_info=SegmentInfo(
                setting=SegmentSetting(indexes=["embedding", "full_text"])
            ),
        )

        success = engine.activate()

        self.assertTrue(success)
        self.assertTrue(any(index.type == "embedding" for index in engine.engine.context.index_result))
        self.assertTrue(any(index.type == "full_text" for index in engine.engine.context.index_result))

        full_text_indexes = [
            index for index in engine.engine.context.index_result if index.type == "full_text"
        ]
        self.assertTrue(full_text_indexes)
        self.assertIn("keywords", full_text_indexes[0].metadata)
        self.assertIn("test", full_text_indexes[0].metadata["keywords"])

    def test_rag_engine_graph_disabled_by_default(self):
        file_path = os.path.abspath(self.test_file)
        engine = RagEngine(file_path)

        with self.assertRaises(RuntimeError):
            engine.get_graph_summary()

    def test_rag_engine_graph_local(self):
        file_path = os.path.abspath(self.test_file)
        graph_info = SegmentInfo(
            setting=SegmentSetting(
                graph=GraphConfig(
                    enabled=True,
                    storage=GraphStorageConfig(backend="memory", graph_name="test_graph"),
                )
            )
        )
        engine = RagEngine(file_path, segment_info=graph_info)

        success = engine.activate()
        self.assertTrue(success)

        summary = engine.get_graph_summary()
        self.assertEqual(summary.graph_name, "test_graph")
        self.assertEqual(summary.backend, "memory")
        self.assertGreater(summary.node_count, 0)

        nodes = engine.list_graph_nodes(limit=10)
        self.assertGreater(len(nodes), 0)

        subgraph = engine.get_subgraph([nodes[0].id], max_hops=1)
        self.assertGreaterEqual(len(subgraph.nodes), 1)

        results = engine.graph_search("Title", top_k=3)
        self.assertGreater(len(results), 0)
        self.assertIn("Title", results[0].metadata["matched_node"])
        self.assertEqual(engine.engine.context.segment_info.status.graph.status, 1)

    def test_rag_engine_graph_requires_activate(self):
        file_path = os.path.abspath(self.test_file)
        graph_info = SegmentInfo(
            setting=SegmentSetting(
                graph=GraphConfig(enabled=True)
            )
        )
        engine = RagEngine(file_path, segment_info=graph_info)

        with self.assertRaises(RuntimeError):
            engine.graph_search("Title")

if __name__ == "__main__":
    unittest.main()
