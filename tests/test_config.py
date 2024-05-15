import unittest
from unittest.mock import Mock, patch
from config_stash.config import Config
from config_stash.loaders.yaml_loader import YamlLoader
from config_stash.loaders.json_loader import JsonLoader

class TestConfig(unittest.TestCase):
    @patch('config_stash.loaders.yaml_loader.YamlLoader.load')
    @patch('config_stash.loaders.json_loader.JsonLoader.load')
    def setUp(self, mock_json_load, mock_yaml_load):
        mock_yaml_load.return_value = {
            'default': {
                'some_env': {
                    'name': {
                        'is': 'yaml_value'
                    }
                }
            }
        }
        mock_json_load.return_value = {
            'default': {
                'some_env': {
                    'name': {
                        'isa': 'json_value'
                    }
                }
            }
        }
        loaders = [
            YamlLoader('config.yaml'),
            JsonLoader('config.json')
        ]
        self.config = Config(env='default', loaders=loaders, dynamic_reloading=False)

    def test_getattr(self):
        self.assertEqual(self.config.some_env.name.isa, 'json_value')

    def test_get_source(self):
        self.assertEqual(self.config.get_source('some_env.name.isa'), 'json')

    def test_reload(self):
        self.config.reload()
        self.assertEqual(self.config.some_env.name.isa, 'json_value')

    def test_extend_config(self):
        mock_loader = Mock()
        mock_loader.load.return_value = {
            'default': {
                'new_key': 'new_value'
            }
        }
        self.config.extend_config(mock_loader)
        self.assertEqual(self.config.new_key, 'new_value')

if __name__ == '__main__':
    unittest.main()