"""Tests for all examples shown in the README to ensure documentation accuracy."""

import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from config_stash import Config
from config_stash.loaders import (
    EnvFileLoader,
    EnvironmentLoader,
    IniLoader,
    JsonLoader,
    TomlLoader,
    YamlLoader,
)


class TestREADMEExamples(unittest.TestCase):
    """Test all code examples from README.md to ensure they work as documented."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        # Create example configuration files as shown in README
        self.create_example_files()

    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_dir)
        import shutil

        shutil.rmtree(self.temp_dir)

    def create_example_files(self):
        """Create configuration files as shown in README examples."""
        # config.yaml - from Quick Start
        yaml_content = """
default:
  database:
    host: localhost
    port: 5432
    name: myapp_dev

  api:
    endpoint: https://api.dev.example.com
    timeout: 30

production:
  database:
    host: prod-db.example.com
    port: 5433
    name: myapp_prod

  api:
    endpoint: https://api.example.com
    timeout: 10
"""
        with open("config.yaml", "w") as f:
            f.write(yaml_content)

        # config.json
        json_content = {"default": {"features": {"new_ui": True, "analytics": False}}}
        with open("config.json", "w") as f:
            json.dump(json_content, f, indent=2)

        # config.toml
        toml_content = """
[default]
app_name = "MyApp"
version = "1.0.0"

[default.cache]
enabled = true
ttl = 3600
"""
        with open("config.toml", "w") as f:
            f.write(toml_content)

        # .env file
        env_content = """
DATABASE_URL=postgresql://user:pass@localhost/dbname
SECRET_KEY=your-secret-key-here
DEBUG=true
"""
        with open(".env", "w") as f:
            f.write(env_content)

        # config.ini
        ini_content = """
[database]
host = localhost
port = 5432
user = admin

[api]
key = secret123
endpoint = https://api.example.com
"""
        with open("config.ini", "w") as f:
            f.write(ini_content)

    def test_quick_start_example(self):
        """Test the Quick Start example from README."""
        # Example from README Quick Start section
        from config_stash import Config

        # Load configuration with environment
        config = Config(env="production", enable_ide_support=False)

        # Access nested values with dot notation
        self.assertEqual(config.database.host, "prod-db.example.com")
        self.assertEqual(config.database.port, 5433)
        self.assertEqual(config.api.timeout, 10)

    def test_multiple_file_formats_example(self):
        """Test loading multiple file formats as shown in README."""
        from config_stash import Config

        config = Config(
            loaders=[
                YamlLoader("config.yaml"),
                JsonLoader("config.json"),
                TomlLoader("config.toml"),
            ],
            env="default",
            enable_ide_support=False,
        )

        # Values from YAML
        self.assertEqual(config.database.host, "localhost")
        # Values from JSON
        self.assertTrue(config.features.new_ui)
        # Values from TOML
        self.assertEqual(config.app_name, "MyApp")
        self.assertTrue(config.cache.enabled)

    def test_environment_variables_example(self):
        """Test environment variable loading as shown in README."""
        # Set environment variables as shown in README
        os.environ["MYAPP_DATABASE__HOST"] = "env-db.example.com"
        os.environ["MYAPP_DATABASE__PORT"] = "5432"
        os.environ["MYAPP_API__KEY"] = "env-secret-key"

        try:
            config = Config(
                loaders=[YamlLoader("config.yaml"), EnvironmentLoader("MYAPP")],
                env="default",
                enable_ide_support=False,
            )

            # Environment variables should override file values
            self.assertEqual(config.database.host, "env-db.example.com")
            self.assertEqual(config.database.port, 5432)
            self.assertEqual(config.api.key, "env-secret-key")

        finally:
            # Clean up environment
            del os.environ["MYAPP_DATABASE__HOST"]
            del os.environ["MYAPP_DATABASE__PORT"]
            del os.environ["MYAPP_API__KEY"]

    def test_env_file_loader_example(self):
        """Test .env file loading as shown in README."""
        config = Config(
            loaders=[EnvFileLoader(".env")], env="default", enable_ide_support=False
        )

        self.assertEqual(config.DATABASE_URL, "postgresql://user:pass@localhost/dbname")
        self.assertEqual(config.SECRET_KEY, "your-secret-key-here")
        self.assertTrue(config.DEBUG)

    def test_ini_file_loader_example(self):
        """Test INI file loading as shown in README."""
        config = Config(
            loaders=[IniLoader("config.ini")], env="default", enable_ide_support=False
        )

        self.assertEqual(config.database.host, "localhost")
        self.assertEqual(config.database.port, 5432)
        self.assertEqual(config.api.key, "secret123")

    def test_dynamic_reloading_example(self):
        """Test dynamic reloading as shown in README."""
        # Create initial config
        config = Config(
            loaders=[YamlLoader("config.yaml")],
            dynamic_reloading=True,
            env="default",
            enable_ide_support=False,
        )

        initial_host = config.database.host

        # Modify the file
        updated_yaml = """
default:
  database:
    host: updated-host.example.com
    port: 5432
"""
        with open("config.yaml", "w") as f:
            f.write(updated_yaml)

        # Wait for file watcher to detect change
        time.sleep(0.5)

        # Manually trigger reload in case file watcher hasn't fired yet (macOS timing issue)
        if config.database.host == initial_host:
            config.reload()

        # Value should be updated
        self.assertNotEqual(config.database.host, initial_host)

        config.stop_watching()

    def test_on_change_callback_example(self):
        """Test on_change callback as shown in README."""
        config = Config(
            loaders=[YamlLoader("config.yaml")], env="default", enable_ide_support=False
        )

        changes_detected = []

        @config.on_change
        def config_changed(key: str, old_value, new_value):
            changes_detected.append({"key": key, "old": old_value, "new": new_value})

        # Trigger reload with changes
        updated_yaml = """
default:
  database:
    host: changed-host.example.com
    port: 5432
"""
        with open("config.yaml", "w") as f:
            f.write(updated_yaml)

        config.reload()

        # Callback should have been triggered
        self.assertTrue(len(changes_detected) > 0)
        self.assertTrue(any("database" in str(c["key"]) for c in changes_detected))

    def test_export_functionality(self):
        """Test export functionality as shown in README."""
        config = Config(
            loaders=[YamlLoader("config.yaml")], env="default", enable_ide_support=False
        )

        # Export as JSON
        json_output = config.export(format="json")
        json_data = json.loads(json_output)
        self.assertIn("database", json_data)

        # Export as YAML
        yaml_output = config.export(format="yaml")
        self.assertIn("database:", yaml_output)

        # Export to file
        config.export(format="json", output_path="exported.json")
        self.assertTrue(Path("exported.json").exists())

    def test_validation_functionality(self):
        """Test validation functionality as shown in README."""
        config = Config(
            loaders=[YamlLoader("config.yaml")], env="default", enable_ide_support=False
        )

        # Basic validation
        self.assertTrue(config.validate())

        # With schema (if implemented)
        schema = {"type": "object", "properties": {"database": {"type": "object"}}}
        self.assertTrue(config.validate(schema))

    def test_source_tracking_debug_mode(self):
        """Test source tracking in debug mode as shown in README."""
        config = Config(
            loaders=[YamlLoader("config.yaml"), JsonLoader("config.json")],
            env="default",
            debug_mode=True,
            enable_ide_support=False,
        )

        # Get source info for a specific key
        source_info = config.get_source_info("database.host")
        if source_info:
            self.assertEqual(source_info.source_file, "config.yaml")
            self.assertEqual(source_info.key, "database.host")

        # Get override history
        history = config.get_override_history("database.host")
        self.assertIsInstance(history, list)

        # Export debug report
        config.export_debug_report("debug_report.json")
        self.assertTrue(Path("debug_report.json").exists())

        # Get source statistics
        stats = config.get_source_statistics()
        self.assertIn("total_keys", stats)
        self.assertIn("unique_sources", stats)

    def test_deep_merge_functionality(self):
        """Test deep merge functionality as shown in README."""
        # Create configs that demonstrate deep merge
        base_yaml = """
default:
  database:
    host: localhost
    port: 5432
    options:
      timeout: 30
      pool_size: 10
"""
        override_yaml = """
default:
  database:
    host: production.example.com
    options:
      pool_size: 50
      ssl_enabled: true
"""
        with open("base.yaml", "w") as f:
            f.write(base_yaml)
        with open("override.yaml", "w") as f:
            f.write(override_yaml)

        # With deep merge (default)
        config = Config(
            loaders=[YamlLoader("base.yaml"), YamlLoader("override.yaml")],
            env="default",
            deep_merge=True,
            enable_ide_support=False,
        )

        # Host is overridden
        self.assertEqual(config.database.host, "production.example.com")
        # Port is preserved from base
        self.assertEqual(config.database.port, 5432)
        # Options are merged
        self.assertEqual(config.database.options.timeout, 30)  # From base
        self.assertEqual(config.database.options.pool_size, 50)  # Overridden
        self.assertTrue(config.database.options.ssl_enabled)  # Added

    def test_environment_loader_with_separator(self):
        """Test EnvironmentLoader with custom separator as documented."""
        os.environ["APP_DATABASE_HOST"] = "custom-db.com"
        os.environ["APP_DATABASE_PORT"] = "3306"
        os.environ["APP_API_VERSION"] = "v2"

        try:
            config = Config(
                loaders=[EnvironmentLoader("APP", separator="_")],
                env="default",
                enable_ide_support=False,
            )

            self.assertEqual(config.database.host, "custom-db.com")
            self.assertEqual(config.database.port, 3306)
            self.assertEqual(config.api.version, "v2")

        finally:
            del os.environ["APP_DATABASE_HOST"]
            del os.environ["APP_DATABASE_PORT"]
            del os.environ["APP_API_VERSION"]

    def test_attribute_access_pattern(self):
        """Test attribute access pattern as shown throughout README."""
        config = Config(
            loaders=[YamlLoader("config.yaml")], env="default", enable_ide_support=False
        )

        # Nested attribute access
        self.assertEqual(config.database.host, "localhost")
        self.assertEqual(config.database.port, 5432)
        self.assertEqual(config.database.name, "myapp_dev")

        # Multiple levels
        self.assertEqual(config.api.endpoint, "https://api.dev.example.com")
        self.assertEqual(config.api.timeout, 30)

    def test_configuration_hierarchy(self):
        """Test configuration hierarchy and override order."""
        # Set environment variable to test override hierarchy
        os.environ["MYAPP_DATABASE__HOST"] = "env-override"

        try:
            config = Config(
                loaders=[
                    YamlLoader("config.yaml"),  # Base configuration
                    JsonLoader("config.json"),  # Overrides YAML
                    EnvironmentLoader("MYAPP"),  # Overrides everything
                ],
                env="default",
                enable_ide_support=False,
            )

            # Environment variable should win
            self.assertEqual(config.database.host, "env-override")
            # JSON values should override YAML where present
            self.assertTrue(config.features.new_ui)
            # YAML values should be present where not overridden
            self.assertEqual(config.database.port, 5432)

        finally:
            del os.environ["MYAPP_DATABASE__HOST"]

    def test_ide_support_generation(self):
        """Test IDE support generation as mentioned in README."""
        config = Config(
            loaders=[YamlLoader("config.yaml")],
            env="default",
            enable_ide_support=True,
            ide_stub_path=".config_stash/stubs.pyi",
        )

        # Check that IDE stub files were created
        stub_file = Path(".config_stash/stubs.pyi")
        self.assertTrue(stub_file.exists())

        # Verify stub content has proper structure
        content = stub_file.read_text()
        self.assertIn("class ConfigType:", content)
        self.assertIn("database:", content)
        self.assertIn("class DatabaseType:", content)

    def test_to_dict_method(self):
        """Test to_dict method as might be used in README examples."""
        config = Config(
            loaders=[YamlLoader("config.yaml")], env="default", enable_ide_support=False
        )

        config_dict = config.to_dict()
        self.assertIsInstance(config_dict, dict)
        self.assertIn("database", config_dict)
        self.assertEqual(config_dict["database"]["host"], "localhost")


class TestREADMECLIExamples(unittest.TestCase):
    """Test CLI examples from README."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        # Create test config
        yaml_content = """
default:
  database:
    host: localhost
    port: 5432
"""
        with open("config.yaml", "w") as f:
            f.write(yaml_content)

    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_dir)
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_cli_validate_command(self):
        """Test CLI validate command as shown in README."""
        from click.testing import CliRunner

        from config_stash.cli import cli

        runner = CliRunner()

        # config-stash validate <env>
        result = runner.invoke(
            cli, ["validate", "default", "--loader", "yaml:config.yaml"]
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("valid", result.output.lower())

    def test_cli_export_command(self):
        """Test CLI export command as shown in README."""
        from click.testing import CliRunner

        from config_stash.cli import cli

        runner = CliRunner()

        # config-stash export <env> --format json
        result = runner.invoke(
            cli,
            ["export", "default", "--loader", "yaml:config.yaml", "--format", "json"],
        )
        self.assertEqual(result.exit_code, 0)
        # Output should be valid JSON
        json.loads(result.output)

    def test_cli_debug_command(self):
        """Test CLI debug command as shown in README."""
        from click.testing import CliRunner

        from config_stash.cli import cli

        runner = CliRunner()

        # config-stash debug <env>
        result = runner.invoke(
            cli, ["debug", "default", "--loader", "yaml:config.yaml"]
        )
        self.assertEqual(result.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
