import unittest
from unittest.mock import Mock
from config_stash.source_tracker import SourceTracker

class TestSourceTracker(unittest.TestCase):
    def setUp(self):
        mock_loader1 = Mock()
        mock_loader1.config = {'key1': 'value1', 'nested': {'key2': 'value2'}}
        mock_loader1.source = 'source1'
        
        mock_loader2 = Mock()
        mock_loader2.config = {'key1': 'new_value1', 'nested': {'key3': 'value3'}}
        mock_loader2.source = 'source2'
        
        self.source_tracker = SourceTracker([mock_loader1, mock_loader2])

    def test_get_source(self):
        self.assertEqual(self.source_tracker.get_source('key1'), 'source2')
        self.assertEqual(self.source_tracker.get_source('nested.key2'), 'source1')
        self.assertEqual(self.source_tracker.get_source('nested.key3'), 'source2')
        self.assertIsNone(self.source_tracker.get_source('non_existent'))

if __name__ == '__main__':
    unittest.main()