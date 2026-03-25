"""Comprehensive tests for deep_merge functionality."""

import os
import tempfile
import unittest
from pathlib import Path

from config_stash import Config
from config_stash.config_merger import ConfigMerger
from config_stash.loaders import JsonLoader, YamlLoader


class TestDeepMergeComprehensive(unittest.TestCase):
    """Comprehensive tests for deep merge functionality."""

    # pyright: reportOptionalSubscript=false, reportOptionalMemberAccess=false
    # pyright: reportArgumentType=false, reportPossiblyUnboundVariable=false
    # pyright: reportAttributeAccessIssue=false, reportCallIssue=false
    # pyright: reportMissingImports=false

    def test_shallow_merge_behavior(self):
        """Test shallow merge replaces entire nested structures."""
        configs = [
            (
                {
                    "database": {
                        "host": "localhost",
                        "port": 5432,
                        "credentials": {"user": "admin", "password": "secret"},
                    }
                },
                "source1",
            ),
            ({"database": {"host": "production.db.com", "ssl": True}}, "source2"),
        ]

        # Shallow merge (default=False)
        merged = ConfigMerger.merge_configs(configs, deep_merge=False)

        # Entire database object is replaced
        self.assertEqual(merged["database"]["host"], "production.db.com")
        self.assertEqual(merged["database"]["ssl"], True)
        # Original nested values are lost
        self.assertNotIn("port", merged["database"])
        self.assertNotIn("credentials", merged["database"])

    def test_deep_merge_behavior(self):
        """Test deep merge preserves and merges nested structures."""
        configs = [
            (
                {
                    "database": {
                        "host": "localhost",
                        "port": 5432,
                        "credentials": {"user": "admin", "password": "secret"},
                    }
                },
                "source1",
            ),
            ({"database": {"host": "production.db.com", "ssl": True}}, "source2"),
        ]

        # Deep merge
        merged = ConfigMerger.merge_configs(configs, deep_merge=True)

        # New values override
        self.assertEqual(merged["database"]["host"], "production.db.com")
        self.assertEqual(merged["database"]["ssl"], True)
        # Original values are preserved
        self.assertEqual(merged["database"]["port"], 5432)
        self.assertEqual(merged["database"]["credentials"]["user"], "admin")
        self.assertEqual(merged["database"]["credentials"]["password"], "secret")

    def test_deeply_nested_structures(self):
        """Test deep merge with 4+ levels of nesting."""
        configs = [
            (
                {
                    "level1": {
                        "level2": {
                            "level3": {
                                "level4": {
                                    "level5": {"value": "original", "keep": "this"}
                                },
                                "other": "data",
                            },
                            "preserve": "me",
                        }
                    }
                },
                "source1",
            ),
            (
                {
                    "level1": {
                        "level2": {
                            "level3": {
                                "level4": {
                                    "level5": {"value": "updated", "new": "added"}
                                }
                            },
                            "also_add": "this",
                        }
                    }
                },
                "source2",
            ),
        ]

        merged = ConfigMerger.merge_configs(configs, deep_merge=True)

        # Check deep updates
        self.assertEqual(
            merged["level1"]["level2"]["level3"]["level4"]["level5"]["value"], "updated"
        )
        self.assertEqual(
            merged["level1"]["level2"]["level3"]["level4"]["level5"]["new"], "added"
        )
        # Check preservation
        self.assertEqual(
            merged["level1"]["level2"]["level3"]["level4"]["level5"]["keep"], "this"
        )
        self.assertEqual(merged["level1"]["level2"]["level3"]["other"], "data")
        self.assertEqual(merged["level1"]["level2"]["preserve"], "me")
        self.assertEqual(merged["level1"]["level2"]["also_add"], "this")

    def test_list_handling_in_merge(self):
        """Test how lists are handled during merge."""
        configs = [
            (
                {
                    "servers": ["server1", "server2"],
                    "ports": [8080, 8081],
                    "features": {"enabled": ["feature1", "feature2"]},
                },
                "source1",
            ),
            (
                {
                    "servers": ["server3", "server4"],
                    "ports": [9090],
                    "features": {"enabled": ["feature3"], "disabled": ["feature4"]},
                },
                "source2",
            ),
        ]

        # Deep merge with lists
        merged = ConfigMerger.merge_configs(configs, deep_merge=True)

        # Lists are typically replaced, not merged
        self.assertEqual(merged["servers"], ["server3", "server4"])
        self.assertEqual(merged["ports"], [9090])
        self.assertEqual(merged["features"]["enabled"], ["feature3"])
        self.assertEqual(merged["features"]["disabled"], ["feature4"])

    def test_none_value_handling(self):
        """Test handling of None values in merge."""
        configs = [
            (
                {
                    "key1": "value1",
                    "key2": "value2",
                    "nested": {"a": "alpha", "b": "beta"},
                },
                "source1",
            ),
            (
                {
                    "key1": None,  # Explicitly set to None
                    "key3": "value3",
                    "nested": {"a": None, "c": "gamma"},
                },
                "source2",
            ),
        ]

        merged = ConfigMerger.merge_configs(configs, deep_merge=True)

        # None should override previous values
        self.assertIsNone(merged["key1"])
        self.assertEqual(merged["key2"], "value2")
        self.assertEqual(merged["key3"], "value3")
        self.assertIsNone(merged["nested"]["a"])
        self.assertEqual(merged["nested"]["b"], "beta")
        self.assertEqual(merged["nested"]["c"], "gamma")

    def test_empty_dict_handling(self):
        """Test handling of empty dicts in merge."""
        configs = [
            (
                {
                    "section1": {"data": "value", "nested": {"key": "value"}},
                    "section2": {"items": ["a", "b"]},
                },
                "source1",
            ),
            (
                {
                    "section1": {},  # Empty dict
                    "section2": {"items": [], "new": "value"},  # Empty list
                },
                "source2",
            ),
        ]

        # Test shallow merge
        shallow = ConfigMerger.merge_configs(configs, deep_merge=False)
        self.assertEqual(shallow["section1"], {})  # Replaced with empty

        # Test deep merge
        deep = ConfigMerger.merge_configs(configs, deep_merge=True)
        # Empty dict doesn't wipe existing in deep merge
        self.assertEqual(deep["section1"]["data"], "value")
        self.assertEqual(deep["section1"]["nested"]["key"], "value")
        self.assertEqual(deep["section2"]["items"], [])  # List is replaced
        self.assertEqual(deep["section2"]["new"], "value")

    def test_type_mismatch_handling(self):
        """Test behavior when merging different types."""
        configs = [
            (
                {
                    "value1": "string",
                    "value2": 42,
                    "value3": {"nested": "dict"},
                    "value4": ["list", "of", "items"],
                },
                "source1",
            ),
            (
                {
                    "value1": 123,  # String -> Int
                    "value2": "string",  # Int -> String
                    "value3": "not_a_dict",  # Dict -> String
                    "value4": {"now": "dict"},  # List -> Dict
                },
                "source2",
            ),
        ]

        merged = ConfigMerger.merge_configs(configs, deep_merge=True)

        # Later values should win regardless of type
        self.assertEqual(merged["value1"], 123)
        self.assertEqual(merged["value2"], "string")
        self.assertEqual(merged["value3"], "not_a_dict")
        self.assertEqual(merged["value4"], {"now": "dict"})

    def test_multiple_source_deep_merge(self):
        """Test deep merge with 3+ configuration sources."""
        configs = [
            (
                {
                    "app": {
                        "name": "MyApp",
                        "version": "1.0",
                        "features": {"auth": True, "logging": True},
                    }
                },
                "base",
            ),
            (
                {
                    "app": {
                        "version": "2.0",
                        "features": {"cache": True, "api": True},
                        "database": {"host": "localhost"},
                    }
                },
                "override1",
            ),
            (
                {
                    "app": {
                        "features": {"auth": False, "monitoring": True},  # Override
                        "database": {"port": 5432},
                    }
                },
                "override2",
            ),
        ]

        merged = ConfigMerger.merge_configs(configs, deep_merge=True)

        self.assertEqual(merged["app"]["name"], "MyApp")
        self.assertEqual(merged["app"]["version"], "2.0")
        # All features should be present
        self.assertFalse(merged["app"]["features"]["auth"])  # Overridden
        self.assertTrue(merged["app"]["features"]["logging"])
        self.assertTrue(merged["app"]["features"]["cache"])
        self.assertTrue(merged["app"]["features"]["api"])
        self.assertTrue(merged["app"]["features"]["monitoring"])
        # Database should have both values
        self.assertEqual(merged["app"]["database"]["host"], "localhost")
        self.assertEqual(merged["app"]["database"]["port"], 5432)

    def test_circular_reference_handling(self):
        """Test that circular references don't cause infinite loops."""
        # Create configs with potential circular structure
        dict1 = {"a": {"b": {}}}
        dict1["a"]["b"]["c"] = dict1["a"]  # Circular reference

        dict2 = {"a": {"d": "value"}}

        configs = [(dict1, "source1"), (dict2, "source2")]

        # Should not crash or infinite loop
        try:
            merged = ConfigMerger.merge_configs(configs, deep_merge=True)
            # Basic check that merge completed
            self.assertIn("a", merged)
        except RecursionError:
            self.fail("Deep merge caused infinite recursion")

    def test_deep_merge_with_config_class(self):
        """Test deep_merge parameter in Config class."""
        temp_dir = tempfile.mkdtemp()
        original_dir = os.getcwd()
        os.chdir(temp_dir)

        try:
            # Create base config
            base_config = """
default:
  database:
    host: localhost
    port: 5432
    options:
      ssl: false
      timeout: 30
  features:
    auth: true
    cache: true
"""
            with open("base.yaml", "w") as f:
                f.write(base_config)

            # Create override config
            override_config = """
default:
  database:
    host: production.db.com
    options:
      ssl: true
      pool_size: 20
  features:
    monitoring: true
"""
            with open("override.yaml", "w") as f:
                f.write(override_config)

            # Test with deep_merge=True (default)
            config_deep = Config(
                loaders=[YamlLoader("base.yaml"), YamlLoader("override.yaml")],
                env="default",
                deep_merge=True,
                enable_ide_support=False,
            )

            # Verify deep merge behavior
            self.assertEqual(config_deep.database.host, "production.db.com")
            self.assertEqual(config_deep.database.port, 5432)  # Preserved
            self.assertTrue(config_deep.database.options.ssl)  # Updated
            self.assertEqual(config_deep.database.options.timeout, 30)  # Preserved
            self.assertEqual(config_deep.database.options.pool_size, 20)  # Added
            self.assertTrue(config_deep.features.auth)  # Preserved
            self.assertTrue(config_deep.features.cache)  # Preserved
            self.assertTrue(config_deep.features.monitoring)  # Added

            # Test with deep_merge=False
            config_shallow = Config(
                loaders=[YamlLoader("base.yaml"), YamlLoader("override.yaml")],
                env="default",
                deep_merge=False,
                enable_ide_support=False,
            )

            # Verify shallow merge behavior
            self.assertEqual(config_shallow.database.host, "production.db.com")
            self.assertFalse(hasattr(config_shallow.database, "port"))  # Lost
            self.assertTrue(config_shallow.database.options.ssl)
            self.assertFalse(
                hasattr(config_shallow.database.options, "timeout")
            )  # Lost
            self.assertFalse(hasattr(config_shallow.features, "auth"))  # Lost
            self.assertFalse(hasattr(config_shallow.features, "cache"))  # Lost
            self.assertTrue(config_shallow.features.monitoring)

        finally:
            os.chdir(original_dir)
            import shutil

            shutil.rmtree(temp_dir)

    def test_special_keys_preservation(self):
        """Test preservation of special keys like __name__, __file__, etc."""
        configs = [
            (
                {
                    "__version__": "1.0.0",
                    "__author__": "Original Author",
                    "data": {"__internal__": "value1", "normal": "value2"},
                },
                "source1",
            ),
            (
                {
                    "__version__": "2.0.0",
                    "data": {"__internal__": "updated", "additional": "value3"},
                },
                "source2",
            ),
        ]

        merged = ConfigMerger.merge_configs(configs, deep_merge=True)

        self.assertEqual(merged["__version__"], "2.0.0")
        self.assertEqual(merged["__author__"], "Original Author")  # Preserved
        self.assertEqual(merged["data"]["__internal__"], "updated")
        self.assertEqual(merged["data"]["normal"], "value2")
        self.assertEqual(merged["data"]["additional"], "value3")

    def test_unicode_and_special_chars(self):
        """Test deep merge with Unicode and special characters."""
        configs = [
            (
                {
                    "messages": {"greeting": "Hello", "unicode": "你好", "emoji": "🚀"},
                    "paths": {"windows": "C:\\Users\\Docs", "unix": "/home/user"},
                },
                "source1",
            ),
            (
                {
                    "messages": {
                        "greeting": "Bonjour",
                        "special": "café",
                        "emoji": "🎉",
                    },
                    "paths": {"network": "\\\\server\\share"},
                },
                "source2",
            ),
        ]

        merged = ConfigMerger.merge_configs(configs, deep_merge=True)

        self.assertEqual(merged["messages"]["greeting"], "Bonjour")
        self.assertEqual(merged["messages"]["unicode"], "你好")
        self.assertEqual(merged["messages"]["special"], "café")
        self.assertEqual(merged["messages"]["emoji"], "🎉")
        self.assertEqual(merged["paths"]["windows"], "C:\\Users\\Docs")
        self.assertEqual(merged["paths"]["unix"], "/home/user")
        self.assertEqual(merged["paths"]["network"], "\\\\server\\share")

    def test_performance_with_large_configs(self):
        """Test deep merge performance with large nested structures."""
        import time

        # Create large nested structure
        def create_nested(depth, breadth):
            if depth == 0:
                return f"value_{depth}"
            result = {}
            for i in range(breadth):
                result[f"key_{i}"] = create_nested(depth - 1, breadth)
            return result

        config1 = create_nested(5, 5)  # 5 levels deep, 5 keys per level
        config2 = create_nested(5, 3)  # Partial override

        configs = [(config1, "source1"), (config2, "source2")]

        start_time = time.time()
        merged = ConfigMerger.merge_configs(configs, deep_merge=True)
        end_time = time.time()

        # Should complete in reasonable time (< 1 second for this size)
        self.assertLess(end_time - start_time, 1.0)

        # Verify merge worked
        self.assertIsInstance(merged, dict)
        self.assertTrue(len(merged) > 0)


if __name__ == "__main__":
    unittest.main()
