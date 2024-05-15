import unittest
from config_stash.utils.lazy_loader import LazyLoader

class TestLazyLoader(unittest.TestCase):
    def setUp(self):
        self.config = {'key1': 'value1', 'nested': {'key2': 'value2'}}
        self.lazy_loader = LazyLoader(self.config)

    def test_get(self):
        self.assertEqual(self.lazy_loader.get('key1'), 'value1')
        self.assertEqual(self.lazy_loader.get('nested.key2'), 'value2')
        with self.assertRaises(KeyError):
            self.lazy_loader.get('non_existent')

if __name__ == '__main__':
    unittest.main()