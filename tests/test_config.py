import unittest
from unittest.mock import Mock, patch

from config_stash.config import Config
from config_stash.loaders.json_loader import JsonLoader
from config_stash.loaders.yaml_loader import YamlLoader


class TestConfig(unittest.TestCase):
    @patch("config_stash.loaders.yaml_loader.YamlLoader.load")
    @patch("config_stash.loaders.json_loader.JsonLoader.load")
    def setUp(self, mock_json_load, mock_yaml_load):
        yaml_config = {"default": {"some_env": {"name": {"is": "yaml_value"}}}}
        json_config = {"default": {"some_env": {"name": {"isa": "json_value"}}}}

        # Create loaders first
        loaders = [YamlLoader("config.yaml"), JsonLoader("config.json")]

        # Make the mocks set config attribute when called
        def yaml_side_effect():
            loaders[0].config = yaml_config["default"]  # Store just the env config
            return yaml_config

        def json_side_effect():
            loaders[1].config = json_config["default"]  # Store just the env config
            return json_config

        mock_yaml_load.side_effect = yaml_side_effect
        mock_json_load.side_effect = json_side_effect

        self.config = Config(env="default", loaders=loaders, dynamic_reloading=False)
        self.loaders = loaders  # Store for later use in tests

    def test_getattr(self):
        self.assertEqual(self.config.some_env.name.isa, "json_value")

    def test_get_source(self):
        # get_source returns the full filename, not just the extension
        # The loaders need to have their config attribute set for source tracking to work

        # Ensure loaders have the proper config attribute set for source tracking
        # The config attribute should be the merged/env config, not the full loaded config
        self.loaders[0].config = {"some_env": {"name": {"is": "yaml_value"}}}
        self.loaders[1].config = {"some_env": {"name": {"isa": "json_value"}}}

        # Test that JSON loader is the source for the 'isa' key
        self.assertEqual(self.config.get_source("some_env.name.isa"), "config.json")

        # Test that YAML loader is the source for the 'is' key
        self.assertEqual(self.config.get_source("some_env.name.is"), "config.yaml")

        # Test non-existent key returns None
        self.assertIsNone(self.config.get_source("non.existent.key"))

    @patch("config_stash.loaders.yaml_loader.YamlLoader.load")
    @patch("config_stash.loaders.json_loader.JsonLoader.load")
    def test_reload(self, mock_json_load, mock_yaml_load):
        # Set up the mocks for reload
        yaml_config = {"default": {"some_env": {"name": {"is": "yaml_value"}}}}
        json_config = {"default": {"some_env": {"name": {"isa": "json_value"}}}}

        mock_yaml_load.return_value = yaml_config
        mock_json_load.return_value = json_config

        self.config.reload()
        self.assertEqual(self.config.some_env.name.isa, "json_value")

    def test_extend_config(self):
        mock_loader = Mock()
        mock_loader.load.return_value = {"default": {"new_key": "new_value"}}
        self.config.extend(mock_loader)  # Method is 'extend', not 'extend_config'
        self.assertEqual(self.config.new_key, "new_value")


if __name__ == "__main__":
    unittest.main()
