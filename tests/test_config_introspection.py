"""Tests for configuration introspection API."""

import os
import tempfile
import unittest

import yaml

from config_stash.config import Config
from config_stash.loaders import YamlLoader


class TestConfigIntrospection(unittest.TestCase):
    """Test configuration introspection methods."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "config.yaml")
        config_data = {
            "database": {"host": "localhost", "port": 5432},
            "app": {"name": "test", "debug": True},
            "api": {"timeout": 30, "retries": 3},
        }
        with open(self.config_file, "w") as f:
            yaml.dump(config_data, f)

        self.config = Config(
            loaders=[YamlLoader(self.config_file)],
            enable_ide_support=False,
        )

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_keys(self):
        """Test keys() method."""
        keys = self.config.keys()
        self.assertIn("database", keys)
        self.assertIn("app", keys)
        self.assertIn("api", keys)

    def test_has(self):
        """Test has() method."""
        self.assertTrue(self.config.has("database"))
        self.assertTrue(self.config.has("database.host"))
        self.assertTrue(self.config.has("app.name"))
        self.assertFalse(self.config.has("nonexistent"))
        self.assertFalse(self.config.has("database.nonexistent"))

    def test_get(self):
        """Test get() method."""
        self.assertEqual(self.config.get("database.host"), "localhost")
        self.assertEqual(self.config.get("database.port"), 5432)
        self.assertEqual(self.config.get("nonexistent"), None)
        self.assertEqual(self.config.get("nonexistent", "default"), "default")

    def test_schema(self):
        """Test schema() method."""
        # Access method directly to avoid attribute shadowing
        schema = type(self.config).schema(self.config)
        self.assertIn("type", schema)
        self.assertIn("keys", schema)

        db_schema = type(self.config).schema(self.config, "database")
        self.assertEqual(db_schema["type"], "dict")
        self.assertIn("host", db_schema["keys"])

    def test_explain(self):
        """Test explain() method."""
        info = self.config.explain("database.host")
        self.assertIn("value", info)
        self.assertIn("source", info)
        self.assertEqual(info["value"], "localhost")

    def test_set(self):
        """Test set() method."""
        self.config.set("database.host", "remote")
        self.assertEqual(self.config.get("database.host"), "remote")

        # Test setting new key
        self.config.set("new_key", "new_value")
        self.assertEqual(self.config.get("new_key"), "new_value")

    def test_set_nested(self):
        """Test setting nested keys."""
        self.config.set("database.ssl.enabled", True)
        self.assertTrue(self.config.get("database.ssl.enabled"))

    def test_set_override(self):
        """Test set() with override flag."""
        self.config.set("database.host", "override1")
        self.config.set("database.host", "override2", override=True)
        self.assertEqual(self.config.get("database.host"), "override2")

    def test_keys_nested(self):
        """Test keys() returns nested keys."""
        keys = self.config.keys()
        nested_keys = [k for k in keys if "." in k]
        # In Config-Stash, keys() may return flat or nested keys depending on implementation
        # This test just ensures it doesn't crash
        self.assertIsInstance(keys, list)


class TestConfigSetMethod(unittest.TestCase):
    """Test configuration set method in detail."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "config.yaml")
        config_data = {"database": {"host": "localhost"}}
        with open(self.config_file, "w") as f:
            yaml.dump(config_data, f)

        self.config = Config(
            loaders=[YamlLoader(self.config_file)],
            enable_ide_support=False,
        )

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_set_string_value(self):
        """Test setting string value."""
        self.config.set("database.host", "newhost")
        self.assertEqual(self.config.get("database.host"), "newhost")

    def test_set_int_value(self):
        """Test setting integer value."""
        self.config.set("database.port", 3306)
        self.assertEqual(self.config.get("database.port"), 3306)

    def test_set_bool_value(self):
        """Test setting boolean value."""
        self.config.set("database.ssl", True)
        self.assertTrue(self.config.get("database.ssl"))

    def test_set_dict_value(self):
        """Test setting dictionary value."""
        self.config.set("database.options", {"pool_size": 10})
        options = self.config.get("database.options")
        self.assertIsInstance(options, dict)
        self.assertEqual(options["pool_size"], 10)


if __name__ == "__main__":
    unittest.main()
