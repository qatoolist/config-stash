"""Tests for configuration export functionality."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import toml
import yaml

from config_stash import Config
from config_stash.exporters import ConfigExporter, add_export_methods


class TestConfigExporter(unittest.TestCase):
    """Test ConfigExporter class."""
# pyright: reportOptionalSubscript=false, reportOptionalMemberAccess=false
# pyright: reportArgumentType=false, reportPossiblyUnboundVariable=false
# pyright: reportAttributeAccessIssue=false, reportCallIssue=false
# pyright: reportMissingImports=false

    def setUp(self):
        """Set up test fixtures."""
        # Create mock config object
        self.mock_config = Mock()
        self.test_data = {
            "database": {"host": "localhost", "port": 5432, "ssl": True},
            "app": {"name": "TestApp", "version": "1.0.0", "debug": False},
            "features": ["auth", "api", "websocket"],
            "max_connections": 100,
        }
        self.mock_config.env_config = self.test_data

    def test_to_dict(self):
        """Test export to dictionary."""
        result = ConfigExporter.to_dict(self.mock_config)
        self.assertEqual(result, self.test_data)

    def test_to_dict_no_env_config(self):
        """Test export when env_config doesn't exist."""
        mock_config = Mock(spec=[])  # No attributes
        result = ConfigExporter.to_dict(mock_config)
        self.assertEqual(result, {})

    def test_to_json(self):
        """Test export to JSON string."""
        json_str = ConfigExporter.to_json(self.mock_config)
        parsed = json.loads(json_str)

        self.assertEqual(parsed, self.test_data)
        # Check formatting
        self.assertIn("\n", json_str)  # Should be indented

    def test_to_json_custom_indent(self):
        """Test JSON export with custom indentation."""
        json_str = ConfigExporter.to_json(self.mock_config, indent=4)
        lines = json_str.split("\n")

        # Check that nested items have 4-space indentation
        for line in lines:
            if line.strip().startswith('"host"'):
                self.assertTrue(line.startswith("    "))  # 4 spaces

    def test_to_yaml(self):
        """Test export to YAML string."""
        yaml_str = ConfigExporter.to_yaml(self.mock_config)
        parsed = yaml.safe_load(yaml_str)

        self.assertEqual(parsed, self.test_data)
        self.assertIn("database:", yaml_str)
        self.assertIn("app:", yaml_str)

    def test_to_yaml_flow_style(self):
        """Test YAML export with flow style."""
        yaml_str = ConfigExporter.to_yaml(self.mock_config, default_flow_style=True)
        # Flow style uses braces and brackets
        self.assertIn("{", yaml_str)

    def test_to_toml(self):
        """Test export to TOML string."""
        toml_str = ConfigExporter.to_toml(self.mock_config)
        parsed = toml.loads(toml_str)

        self.assertEqual(parsed["database"]["host"], "localhost")
        self.assertEqual(parsed["app"]["name"], "TestApp")

    def test_to_env(self):
        """Test export to environment variables."""
        env_str = ConfigExporter.to_env(self.mock_config)
        lines = env_str.split("\n")

        # Check specific environment variables
        self.assertIn("DATABASE_HOST=localhost", lines)
        self.assertIn("DATABASE_PORT=5432", lines)
        self.assertIn("DATABASE_SSL=true", lines)  # Boolean as lowercase
        self.assertIn("APP_NAME=TestApp", lines)
        self.assertIn("APP_DEBUG=false", lines)
        self.assertIn("MAX_CONNECTIONS=100", lines)

        # Check list serialization
        features_line = [l for l in lines if l.startswith("FEATURES=")][0]
        self.assertIn('["auth", "api", "websocket"]', features_line)

    def test_to_env_with_prefix(self):
        """Test environment export with prefix."""
        env_str = ConfigExporter.to_env(self.mock_config, prefix="MYAPP")
        lines = env_str.split("\n")

        self.assertIn("MYAPP_DATABASE_HOST=localhost", lines)
        self.assertIn("MYAPP_APP_NAME=TestApp", lines)

    def test_to_env_custom_separator(self):
        """Test environment export with custom separator."""
        env_str = ConfigExporter.to_env(self.mock_config, separator="__")
        lines = env_str.split("\n")

        self.assertIn("DATABASE__HOST=localhost", lines)
        self.assertIn("APP__NAME=TestApp", lines)

    def test_to_env_nested_dict(self):
        """Test environment export handles nested dictionaries."""
        config = Mock()
        config.env_config = {"level1": {"level2": {"level3": "value"}}}
        env_str = ConfigExporter.to_env(config)
        self.assertIn("LEVEL1_LEVEL2_LEVEL3=value", env_str)

    def test_to_env_none_values(self):
        """Test environment export handles None values."""
        config = Mock()
        config.env_config = {"key": None}
        env_str = ConfigExporter.to_env(config)
        self.assertIn("KEY=", env_str)

    @patch("builtins.open", new_callable=mock_open)
    def test_dump_json(self, mock_file):
        """Test dumping to JSON file."""
        ConfigExporter.dump(self.mock_config, "/tmp/config.json")

        mock_file.assert_called_once_with(Path("/tmp/config.json"), "w")
        handle = mock_file()
        written_content = "".join(call.args[0] for call in handle.write.call_args_list)
        parsed = json.loads(written_content)
        self.assertEqual(parsed, self.test_data)

    @patch("builtins.open", new_callable=mock_open)
    def test_dump_yaml(self, mock_file):
        """Test dumping to YAML file."""
        ConfigExporter.dump(self.mock_config, "/tmp/config.yaml")

        mock_file.assert_called_once_with(Path("/tmp/config.yaml"), "w")
        handle = mock_file()
        written_content = "".join(call.args[0] for call in handle.write.call_args_list)
        parsed = yaml.safe_load(written_content)
        self.assertEqual(parsed["database"]["host"], "localhost")

    @patch("builtins.open", new_callable=mock_open)
    def test_dump_toml(self, mock_file):
        """Test dumping to TOML file."""
        ConfigExporter.dump(self.mock_config, "/tmp/config.toml")

        mock_file.assert_called_once_with(Path("/tmp/config.toml"), "w")
        handle = mock_file()
        written_content = "".join(call.args[0] for call in handle.write.call_args_list)
        parsed = toml.loads(written_content)
        self.assertEqual(parsed["app"]["name"], "TestApp")

    @patch("builtins.open", new_callable=mock_open)
    def test_dump_env(self, mock_file):
        """Test dumping to .env file."""
        ConfigExporter.dump(self.mock_config, "/tmp/.env")

        mock_file.assert_called_once_with(Path("/tmp/.env"), "w")
        handle = mock_file()
        written_content = "".join(call.args[0] for call in handle.write.call_args_list)
        self.assertIn("DATABASE_HOST=localhost", written_content)

    @patch("builtins.open", new_callable=mock_open)
    def test_dump_auto_detect_format(self, mock_file):
        """Test format auto-detection from file extension."""
        # JSON
        ConfigExporter.dump(self.mock_config, "/tmp/config.json")
        written_content = "".join(call.args[0] for call in mock_file().write.call_args_list)
        self.assertTrue(written_content.startswith("{"))  # JSON starts with {

        mock_file.reset_mock()

        # YAML
        ConfigExporter.dump(self.mock_config, "/tmp/config.yml")
        written_content = "".join(call.args[0] for call in mock_file().write.call_args_list)
        self.assertIn(":", written_content)  # YAML has colons

    @patch("builtins.open", new_callable=mock_open)
    def test_dump_explicit_format(self, mock_file):
        """Test explicit format specification overrides extension."""
        ConfigExporter.dump(self.mock_config, "/tmp/config.txt", format="json")
        written_content = "".join(call.args[0] for call in mock_file().write.call_args_list)
        parsed = json.loads(written_content)
        self.assertEqual(parsed, self.test_data)

    def test_dump_invalid_format(self):
        """Test that invalid format raises error."""
        with self.assertRaises(ValueError) as context:
            ConfigExporter.dump(self.mock_config, "/tmp/config", format="invalid")

        self.assertIn("Unknown format", str(context.exception))

    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_dump_creates_parent_dirs(self, mock_file, mock_mkdir):
        """Test that parent directories are created if needed."""
        ConfigExporter.dump(self.mock_config, "/tmp/new/dir/config.json")
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_diff_no_changes(self):
        """Test diff with identical configs."""
        config1 = Mock()
        config1.env_config = {"key": "value"}
        config2 = Mock()
        config2.env_config = {"key": "value"}

        diff_str = ConfigExporter.diff(config1, config2)
        diff_dict = json.loads(diff_str)
        self.assertEqual(diff_dict, {})

    def test_diff_added_keys(self):
        """Test diff with added keys."""
        config1 = Mock()
        config1.env_config = {"existing": "value"}
        config2 = Mock()
        config2.env_config = {"existing": "value", "new": "added"}

        diff_str = ConfigExporter.diff(config1, config2)
        diff_dict = json.loads(diff_str)
        self.assertIn("+ new", diff_dict)
        self.assertEqual(diff_dict["+ new"], "added")

    def test_diff_removed_keys(self):
        """Test diff with removed keys."""
        config1 = Mock()
        config1.env_config = {"old": "value", "keep": "this"}
        config2 = Mock()
        config2.env_config = {"keep": "this"}

        diff_str = ConfigExporter.diff(config1, config2)
        diff_dict = json.loads(diff_str)
        self.assertIn("- old", diff_dict)
        self.assertEqual(diff_dict["- old"], "value")

    def test_diff_modified_values(self):
        """Test diff with modified values."""
        config1 = Mock()
        config1.env_config = {"key": "old_value"}
        config2 = Mock()
        config2.env_config = {"key": "new_value"}

        diff_str = ConfigExporter.diff(config1, config2)
        diff_dict = json.loads(diff_str)
        self.assertIn("~ key", diff_dict)
        self.assertEqual(diff_dict["~ key"]["old"], "old_value")
        self.assertEqual(diff_dict["~ key"]["new"], "new_value")

    def test_diff_nested_changes(self):
        """Test diff with nested dictionary changes."""
        config1 = Mock()
        config1.env_config = {"database": {"host": "localhost", "port": 5432}}
        config2 = Mock()
        config2.env_config = {"database": {"host": "remotehost", "port": 5432, "ssl": True}}

        diff_str = ConfigExporter.diff(config1, config2)
        diff_dict = json.loads(diff_str)
        self.assertIn("~ database.host", diff_dict)
        self.assertIn("+ database.ssl", diff_dict)

    def test_diff_yaml_format(self):
        """Test diff output in YAML format."""
        config1 = Mock()
        config1.env_config = {"old": "value"}
        config2 = Mock()
        config2.env_config = {"new": "value"}

        diff_str = ConfigExporter.diff(config1, config2, format="yaml")
        parsed = yaml.safe_load(diff_str)
        self.assertIn("- old", parsed)
        self.assertIn("+ new", parsed)

    def test_add_export_methods(self):
        """Test adding export methods to Config class."""

        # Create a mock Config class
        class MockConfig:
            env_config = {"test": "data"}

        # Add export methods
        add_export_methods(MockConfig)

        # Check that methods were added
        config = MockConfig()
        self.assertTrue(hasattr(config, "to_dict"))
        self.assertTrue(hasattr(config, "to_json"))
        self.assertTrue(hasattr(config, "to_yaml"))
        self.assertTrue(hasattr(config, "to_toml"))
        self.assertTrue(hasattr(config, "to_env"))
        self.assertTrue(hasattr(config, "dump"))

        # Test that methods work
        result = config.to_dict()
        self.assertEqual(result, {"test": "data"})

        json_result = config.to_json()
        self.assertIn("test", json_result)


class TestExporterIntegration(unittest.TestCase):
    """Integration tests with actual Config class."""

    def test_real_config_export(self):
        """Test export with real Config instance."""
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"default": {"app_name": "IntegrationTest", "port": 8080}}, f)
            config_file = f.name

        try:
            from config_stash.loaders.json_loader import JsonLoader

            # Create config
            config = Config(env="default", loaders=[JsonLoader(config_file)])

            # Add export methods
            add_export_methods(Config)

            # Test export
            exported = config.to_dict()
            self.assertEqual(exported["app_name"], "IntegrationTest")
            self.assertEqual(exported["port"], 8080)

            # Test JSON export
            json_str = config.to_json()
            parsed = json.loads(json_str)
            self.assertEqual(parsed["app_name"], "IntegrationTest")

        finally:
            Path(config_file).unlink()


if __name__ == "__main__":
    unittest.main()
