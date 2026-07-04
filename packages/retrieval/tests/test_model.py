import unittest
from retrieval.model import (
    LoaderConfig, 
    SplitterConfig, 
    SegmentSetting, 
    SegmentStatus, 
    SegmentInfo, 
    IndexStatus,
    GraphConfig,
    GraphStorageConfig,
)

class TestRagModels(unittest.TestCase):

    def test_loader_config_defaults(self):
        config = LoaderConfig()
        self.assertEqual(config.name, "")
        self.assertEqual(config.extractor, "")
        self.assertIsNone(config.kwargs)

    def test_splitter_config_defaults(self):
        config = SplitterConfig()
        self.assertEqual(config.name, "default")

    def test_segment_setting_defaults(self):
        setting = SegmentSetting()
        self.assertEqual(setting.maxLength, 1024)
        self.assertEqual(setting.overlap, 128)  # ~12% of maxLength for cross-boundary context
        self.assertEqual(setting.mode, "default")
        self.assertEqual(setting.indexes, ["embedding"])
        self.assertFalse(setting.graph.enabled)
        self.assertEqual(setting.graph.storage.backend, "memory")
        
        # Check nested defaults
        self.assertIsInstance(setting.loader, LoaderConfig)
        self.assertIsInstance(setting.splitter, SplitterConfig)
        self.assertIsInstance(setting.graph, GraphConfig)

    def test_segment_status_defaults(self):
        status = SegmentStatus()
        self.assertEqual(status.loader.status, 0)
        self.assertEqual(status.splitter.status, 0)
        self.assertEqual(status.indexes, [])
        self.assertEqual(status.graph.status, 0)

    def test_segment_info_defaults(self):
        info = SegmentInfo()
        self.assertIsInstance(info.status, SegmentStatus)
        self.assertIsInstance(info.setting, SegmentSetting)
        self.assertEqual(info.errorMessage, "")

    def test_custom_segment_setting(self):
        setting = SegmentSetting(
            maxLength=2048,
            overlap=200,
            indexes=["embedding", "full_text"],
            loader=LoaderConfig(name="pdf"),
            splitter=SplitterConfig(name="recursive")
        )
        self.assertEqual(setting.maxLength, 2048)
        self.assertEqual(setting.overlap, 200)
        self.assertEqual(setting.indexes, ["embedding", "full_text"])
        self.assertEqual(setting.loader.name, "pdf")
        self.assertEqual(setting.splitter.name, "recursive")

    def test_index_status(self):
        idx = IndexStatus(name="embedding", status=1)
        self.assertEqual(idx.name, "embedding")
        self.assertEqual(idx.status, 1)

    def test_graph_storage_alias(self):
        storage = GraphStorageConfig(schema="kg")
        self.assertEqual(storage.schema_name, "kg")

if __name__ == "__main__":
    unittest.main()
