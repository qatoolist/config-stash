import unittest
from unittest.mock import Mock
from config_stash.config_loader import ConfigLoader

class TestConfigLoader(unittest.TestCase):
    def setUp(self):
        self.mock_loader = Mock()
        self.mock_loader.load.return_value = {'key': 'value'}
        self.loader = ConfigLoader([self.mock_loader])

    def test_load_configs(self):
        configs = self.loader.load_configs()
        self.assertEqual(configs, [({'key': 'value'}, self.mock_loader.source)])

    def test_add_loader(self):
        config, source = self.loader.add_loader(self.mock_loader)
        self.assertEqual(config, {'key': 'value'})
        self.assertEqual(source, self.mock_loader.source)

if __name__ == '__main__':
    unittest.main()