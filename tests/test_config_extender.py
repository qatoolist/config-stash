import unittest
from unittest.mock import Mock
from config_stash.config_extender import ConfigExtender
from config_stash.config import Config

class TestConfigExtender(unittest.TestCase):
    def setUp(self):
        self.config = Mock(spec=Config)
        self.config.merged_config = {}
        self.config.env = 'default'
        self.extender = ConfigExtender(self.config)

    def test_extend(self):
        mock_loader = Mock()
        mock_loader.load.return_value = {
            'default': {
                'extended_key': 'extended_value'
            }
        }
        self.extender.extend(mock_loader)
        self.assertEqual(self.config.attribute_accessor.extended_key, 'extended_value')

if __name__ == '__main__':
    unittest.main()