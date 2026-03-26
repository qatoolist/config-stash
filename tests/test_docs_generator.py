"""Tests for configuration documentation generator."""

import json
import os
import shutil
import tempfile
import unittest

import yaml
from click.testing import CliRunner

from config_stash.cli import cli
from config_stash.config import Config
from config_stash.loaders import YamlLoader


class TestGenerateDocsMarkdown(unittest.TestCase):
    """Test generate_docs() with markdown format."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "config.yaml")
        config_data = {
            "database": {"host": "localhost", "port": 5432, "ssl": True},
            "app": {"name": "myapp", "debug": False},
        }
        with open(self.config_file, "w") as f:
            yaml.dump(config_data, f)

        self.config = Config(
            loaders=[YamlLoader(self.config_file)],
            enable_ide_support=False,
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_returns_string(self):
        """generate_docs returns a non-empty string."""
        docs = self.config.generate_docs()
        self.assertIsInstance(docs, str)
        self.assertTrue(len(docs) > 0)

    def test_markdown_header(self):
        """Markdown output starts with the expected header."""
        docs = self.config.generate_docs()
        self.assertIn("# Configuration Reference", docs)
        self.assertIn("## Keys", docs)

    def test_contains_all_leaf_keys(self):
        """Every leaf key appears in the markdown table."""
        docs = self.config.generate_docs()
        for key in ("database.host", "database.port", "database.ssl",
                     "app.name", "app.debug"):
            self.assertIn(f"`{key}`", docs)

    def test_types_in_output(self):
        """Value types are shown correctly."""
        docs = self.config.generate_docs()
        self.assertIn("str", docs)
        self.assertIn("int", docs)
        self.assertIn("bool", docs)

    def test_values_in_output(self):
        """Current values appear in the output."""
        docs = self.config.generate_docs()
        self.assertIn("localhost", docs)
        self.assertIn("5432", docs)
        self.assertIn("True", docs)
        self.assertIn("myapp", docs)

    def test_source_in_output(self):
        """Source file path appears in the output."""
        docs = self.config.generate_docs()
        # The source should reference our config file
        self.assertIn("config.yaml", docs)

    def test_no_parent_keys_in_table(self):
        """Parent keys (dicts) should not appear as rows."""
        docs = self.config.generate_docs()
        lines = docs.split("\n")
        table_lines = [l for l in lines if l.startswith("|") and "`database`" in l]
        # "database" alone (without .host etc.) should NOT appear
        # because its value is a dict, not a leaf
        for line in table_lines:
            # Ensure it's not just `database` but `database.something`
            self.assertNotRegex(line, r"`database`\s*\|")


class TestGenerateDocsJSON(unittest.TestCase):
    """Test generate_docs() with json format."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "config.yaml")
        config_data = {
            "server": {"host": "0.0.0.0", "port": 8080},
            "feature_flags": {"beta": True},
        }
        with open(self.config_file, "w") as f:
            yaml.dump(config_data, f)

        self.config = Config(
            loaders=[YamlLoader(self.config_file)],
            enable_ide_support=False,
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_valid_json(self):
        """JSON output is valid JSON."""
        docs = self.config.generate_docs(format="json")
        parsed = json.loads(docs)
        self.assertIsInstance(parsed, list)

    def test_json_keys_present(self):
        """Each JSON entry has the expected fields."""
        docs = self.config.generate_docs(format="json")
        parsed = json.loads(docs)
        for entry in parsed:
            self.assertIn("key", entry)
            self.assertIn("type", entry)
            self.assertIn("current_value", entry)
            self.assertIn("source", entry)

    def test_json_values(self):
        """JSON values match the config."""
        docs = self.config.generate_docs(format="json")
        parsed = json.loads(docs)
        by_key = {e["key"]: e for e in parsed}
        self.assertEqual(by_key["server.host"]["current_value"], "0.0.0.0")
        self.assertEqual(by_key["server.port"]["current_value"], 8080)
        self.assertEqual(by_key["feature_flags.beta"]["current_value"], True)

    def test_invalid_format_raises(self):
        """Unsupported format raises ValueError."""
        with self.assertRaises(ValueError):
            self.config.generate_docs(format="html")


class TestGenerateDocsPydantic(unittest.TestCase):
    """Test generate_docs() when a Pydantic schema is provided."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "config.yaml")
        config_data = {
            "database_host": "localhost",
            "database_port": 5432,
            "debug": False,
        }
        with open(self.config_file, "w") as f:
            yaml.dump(config_data, f)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_pydantic_descriptions_in_markdown(self):
        """Pydantic field descriptions appear in markdown output."""
        try:
            from pydantic import BaseModel, Field
        except ImportError:
            self.skipTest("pydantic not installed")

        class AppConfig(BaseModel):
            database_host: str = Field(description="Database hostname")
            database_port: int = Field(default=5432, description="Database port number")
            debug: bool = Field(default=False, description="Enable debug mode")

        config = Config(
            loaders=[YamlLoader(self.config_file)],
            schema=AppConfig,
            validate_on_load=True,
            enable_ide_support=False,
        )

        docs = config.generate_docs()
        self.assertIn("Description", docs)
        self.assertIn("Default", docs)
        self.assertIn("Required", docs)
        self.assertIn("Database hostname", docs)
        self.assertIn("Database port number", docs)
        self.assertIn("Enable debug mode", docs)

    def test_pydantic_required_field(self):
        """Required fields are marked as Yes."""
        try:
            from pydantic import BaseModel, Field
        except ImportError:
            self.skipTest("pydantic not installed")

        class AppConfig(BaseModel):
            database_host: str = Field(description="Database hostname")
            database_port: int = Field(default=5432, description="Database port number")
            debug: bool = Field(default=False, description="Enable debug mode")

        config = Config(
            loaders=[YamlLoader(self.config_file)],
            schema=AppConfig,
            validate_on_load=True,
            enable_ide_support=False,
        )

        docs = config.generate_docs()
        self.assertIn("Yes", docs)  # database_host is required
        self.assertIn("No", docs)   # database_port and debug have defaults

    def test_pydantic_json_format(self):
        """JSON output includes pydantic metadata."""
        try:
            from pydantic import BaseModel, Field
        except ImportError:
            self.skipTest("pydantic not installed")

        class AppConfig(BaseModel):
            database_host: str = Field(description="Database hostname")
            database_port: int = Field(default=5432, description="Database port number")
            debug: bool = Field(default=False, description="Enable debug mode")

        config = Config(
            loaders=[YamlLoader(self.config_file)],
            schema=AppConfig,
            validate_on_load=True,
            enable_ide_support=False,
        )

        docs = config.generate_docs(format="json")
        parsed = json.loads(docs)
        by_key = {e["key"]: e for e in parsed}

        self.assertEqual(by_key["database_host"]["description"], "Database hostname")
        self.assertTrue(by_key["database_host"]["required"])
        self.assertFalse(by_key["database_port"]["required"])


class TestGenerateDocsSourceTracking(unittest.TestCase):
    """Test that source tracking info appears in docs."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "base.yaml")
        config_data = {"app": {"name": "testapp", "version": "1.0"}}
        with open(self.config_file, "w") as f:
            yaml.dump(config_data, f)

        self.config = Config(
            loaders=[YamlLoader(self.config_file)],
            enable_ide_support=False,
            debug_mode=True,
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_source_file_in_markdown(self):
        """Source file names appear in the markdown table."""
        docs = self.config.generate_docs()
        self.assertIn("base.yaml", docs)

    def test_source_file_in_json(self):
        """Source file names appear in JSON output."""
        docs = self.config.generate_docs(format="json")
        parsed = json.loads(docs)
        sources = [e["source"] for e in parsed]
        self.assertTrue(any("base.yaml" in s for s in sources if s))


class TestDocsCLI(unittest.TestCase):
    """Test the 'docs' CLI command."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "config.yaml")
        config_data = {
            "database": {"host": "localhost", "port": 5432},
            "logging": {"level": "INFO"},
        }
        with open(self.config_file, "w") as f:
            yaml.dump(config_data, f)

        self.runner = CliRunner()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_docs_markdown_stdout(self):
        """CLI docs command outputs markdown to stdout."""
        result = self.runner.invoke(
            cli,
            ["docs", "default", "--loader", f"yaml:{self.config_file}"],
        )
        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertIn("# Configuration Reference", result.output)
        self.assertIn("`database.host`", result.output)

    def test_docs_json_stdout(self):
        """CLI docs command outputs json to stdout."""
        result = self.runner.invoke(
            cli,
            [
                "docs", "default",
                "--loader", f"yaml:{self.config_file}",
                "--format", "json",
            ],
        )
        self.assertEqual(result.exit_code, 0, msg=result.output)
        parsed = json.loads(result.output)
        self.assertIsInstance(parsed, list)

    def test_docs_output_file(self):
        """CLI docs command writes to a file when --output is given."""
        output_file = os.path.join(self.temp_dir, "reference.md")
        result = self.runner.invoke(
            cli,
            [
                "docs", "default",
                "--loader", f"yaml:{self.config_file}",
                "--output", output_file,
            ],
        )
        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertTrue(os.path.exists(output_file))
        with open(output_file) as f:
            content = f.read()
        self.assertIn("# Configuration Reference", content)


if __name__ == "__main__":
    unittest.main()
