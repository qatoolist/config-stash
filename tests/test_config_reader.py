import unittest
from unittest.mock import patch
from config_stash.config_reader import read_pyproject_config, get_default_loaders, get_default_settings

class TestConfigReader(unittest.TestCase):
    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data='[tool.config_stash]\ndefault_environment = "production"\n')
    def test_read_pyproject_config(self, mock_open):
        config = read_pyproject_config()
        self.assertEqual(config['default_environment'], 'production')

    @patch('config_stash.config_reader.read_pyproject_config')
    def test_get_default_loaders(self, mock_read_config):
        mock_read_config.return_value = {
            'loaders': {
                'yaml': 'config_stash.loaders.yaml_loader:YamlLoader'
            }
        }
        loaders = get_default_loaders()
        self.assertIn('yaml', loaders)

    @patch('config_stash.config_reader.read_pyproject_config')
    def test_get_default_settings(self, mock_read_config):
        mock_read_config.return_value = {
            'default_environment': 'staging',
            'default_files': ['config.yaml']
        }
        settings = get_default_settings()
        self.assertEqual(settings['default_environment'], 'staging')
        self.assertIn('config.yaml', settings['default_files'])

if __name__ == '__main__':
    unittest.main()