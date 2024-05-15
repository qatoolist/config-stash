import unittest
from unittest.mock import patch, mock_open
from config_stash.loaders.yaml_loader import YamlLoader
from config_stash.loaders.json_loader import JsonLoader
from config_stash.loaders.toml_loader import TomlLoader
from config_stash.loaders.environment_loader import EnvironmentLoader

class TestLoaders(unittest.TestCase):
    @patch('builtins.open', new_callable=mock_open, read_data='key: value')
    @patch('yaml.safe_load')
    def test_yaml_loader(self, mock_safe_load, mock_file):
        mock_safe_load.return_value = {'key': 'value'}
        loader = YamlLoader('config.yaml')
        config = loader.load()
        self.assertEqual(config['key'], 'value')

    @patch('builtins.open', new_callable=mock_open, read_data='{"key": "value"}')
    @patch('json.loads')
    def test_json_loader(self, mock_loads, mock_file):
        mock_loads.return_value = {'key': 'value'}
        loader = JsonLoader('config.json')
        config = loader.load()
        self.assertEqual(config['key'], 'value')

    @patch('builtins.open', new_callable=mock_open, read_data='key = "value"')
    @patch('toml.loads')
    def test_toml_loader(self, mock_loads, mock_file):
        mock_loads.return_value = {'key': 'value'}
        loader = TomlLoader('config.toml')
        config = loader.load()
        self.assertEqual(config['key'], 'value')

    @patch.dict('os.environ', {'PREFIX_KEY__NESTED': 'value'})
    def test_environment_loader(self):
        loader = EnvironmentLoader('PREFIX')
        config = loader.load()
        self.assertEqual(config['key']['nested'], 'value')

if __name__ == '__main__':
    unittest.main()