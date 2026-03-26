"""Comprehensive tests for all CLI commands including validate, export, and debug."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from config_stash.cli import cli


class TestCLICommands(unittest.TestCase):
    """Test all CLI commands comprehensively."""

    def setUp(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        # Create test configuration files
        self.yaml_config = """
default:
  database:
    host: localhost
    port: 5432
    username: admin
  api:
    endpoint: https://api.example.com
    timeout: 30
    retries: 3

production:
  database:
    host: prod.db.example.com
    port: 3306

development:
  database:
    host: dev.db.example.com
"""
        with open("config.yaml", "w") as f:
            f.write(self.yaml_config)

        self.json_config = {"default": {"features": {"auth": True, "cache": False}}}
        with open("config.json", "w") as f:
            json.dump(self.json_config, f)

        # Create a schema file for validation
        self.schema = {
            "type": "object",
            "properties": {
                "database": {
                    "type": "object",
                    "required": ["host", "port"],
                    "properties": {
                        "host": {"type": "string"},
                        "port": {"type": "integer"},
                    },
                }
            },
        }
        with open("schema.json", "w") as f:
            json.dump(self.schema, f)

    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_dir)
        import shutil

        shutil.rmtree(self.temp_dir)

    # ========== VALIDATE COMMAND TESTS ==========

    def test_validate_command_success(self):
        """Test validate command with valid configuration."""
        result = self.runner.invoke(
            cli, ["validate", "default", "--loader", "yaml:config.yaml"]
        )

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Configuration is valid", result.output)

    def test_validate_command_with_schema(self):
        """Test validate command with schema validation."""
        result = self.runner.invoke(
            cli,
            [
                "validate",
                "default",
                "--loader",
                "yaml:config.yaml",
                "--schema",
                "schema.json",
            ],
        )

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Configuration is valid", result.output)

    def test_validate_command_with_invalid_config(self):
        """Test validate command with invalid configuration."""
        # Create an empty config that would be invalid
        with open("empty.yaml", "w") as f:
            f.write("default: {}")

        with patch("config_stash.config.Config.validate", return_value=False):
            result = self.runner.invoke(
                cli, ["validate", "default", "--loader", "yaml:empty.yaml"]
            )

            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("Configuration is invalid", result.output)

    def test_validate_command_with_missing_file(self):
        """Test validate command with missing configuration file."""
        result = self.runner.invoke(
            cli, ["validate", "default", "--loader", "yaml:nonexistent.yaml"]
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Error", result.output)

    def test_validate_command_with_multiple_loaders(self):
        """Test validate command with multiple configuration sources."""
        result = self.runner.invoke(
            cli,
            [
                "validate",
                "default",
                "--loader",
                "yaml:config.yaml",
                "--loader",
                "json:config.json",
            ],
        )

        self.assertEqual(result.exit_code, 0)

    # ========== EXPORT COMMAND TESTS ==========

    def test_export_command_json_format(self):
        """Test export command with JSON format."""
        result = self.runner.invoke(
            cli,
            ["export", "default", "--loader", "yaml:config.yaml", "--format", "json"],
        )

        self.assertEqual(result.exit_code, 0)

        # Verify output is valid JSON
        output_json = json.loads(result.output)
        self.assertIn("database", output_json)
        self.assertEqual(output_json["database"]["host"], "localhost")

    def test_export_command_yaml_format(self):
        """Test export command with YAML format."""
        result = self.runner.invoke(
            cli,
            ["export", "default", "--loader", "yaml:config.yaml", "--format", "yaml"],
        )

        self.assertEqual(result.exit_code, 0)
        self.assertIn("database:", result.output)
        self.assertIn("host:", result.output)

    def test_export_command_toml_format(self):
        """Test export command with TOML format."""
        result = self.runner.invoke(
            cli,
            ["export", "default", "--loader", "yaml:config.yaml", "--format", "toml"],
        )

        self.assertEqual(result.exit_code, 0)
        self.assertIn("[database]", result.output)

    def test_export_command_to_file(self):
        """Test export command with output file."""
        output_file = "exported_config.json"

        result = self.runner.invoke(
            cli,
            [
                "export",
                "default",
                "--loader",
                "yaml:config.yaml",
                "--format",
                "json",
                "--output",
                output_file,
            ],
        )

        self.assertEqual(result.exit_code, 0)
        self.assertIn(f"Configuration exported to {output_file}", result.output)

        # Verify file was created
        self.assertTrue(Path(output_file).exists())

        # Verify file content
        with open(output_file, "r") as f:
            exported = json.load(f)
            self.assertIn("database", exported)

    def test_export_command_with_environment(self):
        """Test export command with different environments."""
        # Export production environment
        result = self.runner.invoke(
            cli,
            [
                "export",
                "production",
                "--loader",
                "yaml:config.yaml",
                "--format",
                "json",
            ],
        )

        self.assertEqual(result.exit_code, 0)
        output_json = json.loads(result.output)

        # Should have production overrides
        self.assertEqual(output_json["database"]["host"], "prod.db.example.com")
        self.assertEqual(output_json["database"]["port"], 3306)

    def test_export_command_with_merged_configs(self):
        """Test export command with multiple config sources merged."""
        result = self.runner.invoke(
            cli,
            [
                "export",
                "default",
                "--loader",
                "yaml:config.yaml",
                "--loader",
                "json:config.json",
                "--format",
                "json",
            ],
        )

        self.assertEqual(result.exit_code, 0)
        output_json = json.loads(result.output)

        # Should have both YAML and JSON configs merged
        self.assertIn("database", output_json)  # From YAML
        self.assertIn("features", output_json)  # From JSON

    # ========== DEBUG COMMAND TESTS ==========

    def test_debug_command_general_info(self):
        """Test debug command showing general debug information."""
        result = self.runner.invoke(
            cli, ["debug", "default", "--loader", "yaml:config.yaml"]
        )

        self.assertEqual(result.exit_code, 0)

    def test_debug_command_specific_key(self):
        """Test debug command for specific configuration key."""
        result = self.runner.invoke(
            cli,
            [
                "debug",
                "default",
                "--loader",
                "yaml:config.yaml",
                "--key",
                "database.host",
            ],
        )

        self.assertEqual(result.exit_code, 0)

    def test_debug_command_with_override_history(self):
        """Test debug command showing override history."""
        # Create multiple config sources for overrides
        with open("override.yaml", "w") as f:
            f.write("""
default:
  database:
    host: overridden.db.com
""")

        result = self.runner.invoke(
            cli,
            [
                "debug",
                "default",
                "--loader",
                "yaml:config.yaml",
                "--loader",
                "yaml:override.yaml",
                "--key",
                "database",
            ],
        )

        self.assertEqual(result.exit_code, 0)

    def test_debug_command_export_report(self):
        """Test debug command exporting debug report to file."""
        report_file = "debug_report.json"

        result = self.runner.invoke(
            cli,
            [
                "debug",
                "default",
                "--loader",
                "yaml:config.yaml",
                "--export-report",
                report_file,
            ],
        )

        self.assertEqual(result.exit_code, 0)
        self.assertIn(f"Debug report exported to {report_file}", result.output)

        # Verify report file was created
        self.assertTrue(Path(report_file).exists())

        # Verify report content
        with open(report_file, "r") as f:
            report = json.load(f)
            self.assertIn("timestamp", report)
            self.assertIn("sources", report)

    def test_debug_command_nonexistent_key(self):
        """Test debug command with nonexistent key."""
        result = self.runner.invoke(
            cli,
            [
                "debug",
                "default",
                "--loader",
                "yaml:config.yaml",
                "--key",
                "nonexistent.key",
            ],
        )

        self.assertEqual(result.exit_code, 0)
        self.assertIn("No source information found", result.output)

    # ========== LOAD COMMAND TESTS (EXISTING) ==========

    def test_load_command(self):
        """Test load command displays merged configuration."""
        result = self.runner.invoke(
            cli, ["load", "default", "--loader", "yaml:config.yaml"]
        )

        self.assertEqual(result.exit_code, 0)
        self.assertIn("database", result.output)

    def test_load_with_dynamic_reloading(self):
        """Test load command with dynamic reloading enabled."""
        result = self.runner.invoke(
            cli,
            ["load", "default", "--loader", "yaml:config.yaml", "--dynamic-reloading"],
        )

        self.assertEqual(result.exit_code, 0)

    def test_load_with_env_expander_disabled(self):
        """Test load command with environment variable expansion disabled."""
        os.environ["TEST_VAR"] = "expanded_value"

        result = self.runner.invoke(
            cli,
            [
                "load",
                "default",
                "--loader",
                "yaml:config.yaml",
                "--no-use-env-expander",
            ],
        )

        self.assertEqual(result.exit_code, 0)
        del os.environ["TEST_VAR"]

    # ========== GET COMMAND TESTS (EXISTING) ==========

    def test_get_command(self):
        """Test get command retrieves specific value."""
        result = self.runner.invoke(
            cli, ["get", "default", "database", "--loader", "yaml:config.yaml"]
        )

        self.assertEqual(result.exit_code, 0)
        self.assertIn("localhost", result.output)

    def test_get_nested_value(self):
        """Test get command with nested configuration key."""
        # Create a test to get nested value using attribute access
        with patch("config_stash.config.Config.__getattr__") as mock_getattr:
            mock_getattr.return_value = {"host": "localhost", "port": 5432}

            result = self.runner.invoke(
                cli, ["get", "default", "database", "--loader", "yaml:config.yaml"]
            )

            self.assertEqual(result.exit_code, 0)

    def test_get_nonexistent_key(self):
        """Test get command with nonexistent key."""
        result = self.runner.invoke(
            cli, ["get", "default", "nonexistent", "--loader", "yaml:config.yaml"]
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Configuration key 'nonexistent' not found", result.output)

    # ========== ERROR HANDLING TESTS ==========

    def test_invalid_loader_spec(self):
        """Test commands with invalid loader specification."""
        result = self.runner.invoke(
            cli, ["load", "default", "--loader", "invalid_spec"]
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Invalid loader spec", result.output)

    def test_unknown_loader_type(self):
        """Test commands with unknown loader type."""
        result = self.runner.invoke(
            cli, ["load", "default", "--loader", "unknown:config.file"]
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Unknown loader type", result.output)

    # ========== INTEGRATION TESTS ==========

    def test_validate_then_export_workflow(self):
        """Test a workflow of validating then exporting configuration."""
        # First validate
        validate_result = self.runner.invoke(
            cli, ["validate", "default", "--loader", "yaml:config.yaml"]
        )
        self.assertEqual(validate_result.exit_code, 0)

        # Then export
        export_result = self.runner.invoke(
            cli,
            [
                "export",
                "default",
                "--loader",
                "yaml:config.yaml",
                "--format",
                "json",
                "--output",
                "validated_config.json",
            ],
        )
        self.assertEqual(export_result.exit_code, 0)

        # Verify exported file exists
        self.assertTrue(Path("validated_config.json").exists())

    def test_debug_with_multiple_environments(self):
        """Test debug command across different environments."""
        for env in ["default", "production", "development"]:
            result = self.runner.invoke(
                cli,
                [
                    "debug",
                    env,
                    "--loader",
                    "yaml:config.yaml",
                    "--key",
                    "database.host",
                ],
            )
            self.assertEqual(result.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
