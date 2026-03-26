"""Comprehensive tests for EnvironmentLoader with custom separator support."""

import os
import unittest
from unittest.mock import patch

from config_stash.loaders import EnvironmentLoader


class TestEnvironmentLoaderSeparator(unittest.TestCase):
    """Test EnvironmentLoader with custom separator functionality."""

    def test_default_separator_double_underscore(self):
        """Test default separator (__) for nested keys."""
        env_vars = {
            "APP_DATABASE__HOST": "localhost",
            "APP_DATABASE__PORT": "5432",
            "APP_API__ENDPOINT": "https://api.example.com",
            "APP_API__TIMEOUT": "30",
            "OTHER_VAR": "ignored",
        }

        with patch.dict("os.environ", env_vars, clear=True):
            loader = EnvironmentLoader("APP")
            config = loader.load()

            self.assertEqual(config["database"]["host"], "localhost")
            self.assertEqual(config["database"]["port"], 5432)
            self.assertEqual(config["api"]["endpoint"], "https://api.example.com")
            self.assertEqual(config["api"]["timeout"], 30)
            self.assertNotIn("other_var", config)

    def test_custom_separator_single_underscore(self):
        """Test custom separator (_) for nested keys."""
        env_vars = {
            "MYAPP_DATABASE_HOST": "prod.db.com",
            "MYAPP_DATABASE_PORT": "3306",
            "MYAPP_DATABASE_SSL_ENABLED": "true",
            "MYAPP_CACHE_REDIS_HOST": "cache.example.com",
            "NOTMYAPP_IGNORED": "value",
        }

        with patch.dict("os.environ", env_vars, clear=True):
            loader = EnvironmentLoader("MYAPP", separator="_")
            config = loader.load()

            self.assertEqual(config["database"]["host"], "prod.db.com")
            self.assertEqual(config["database"]["port"], 3306)
            self.assertEqual(config["database"]["ssl"]["enabled"], True)
            self.assertEqual(config["cache"]["redis"]["host"], "cache.example.com")
            self.assertNotIn("notmyapp", config)

    def test_custom_separator_dot(self):
        """Test custom separator (.) for nested keys."""
        env_vars = {
            "CONFIG_SERVER.HOST": "localhost",
            "CONFIG_SERVER.PORT": "8080",
            "CONFIG_DB.PRIMARY.HOST": "primary.db.com",
            "CONFIG_DB.REPLICA.HOST": "replica.db.com",
        }

        with patch.dict("os.environ", env_vars, clear=True):
            loader = EnvironmentLoader("CONFIG", separator=".")
            config = loader.load()

            self.assertEqual(config["server"]["host"], "localhost")
            self.assertEqual(config["server"]["port"], 8080)
            self.assertEqual(config["db"]["primary"]["host"], "primary.db.com")
            self.assertEqual(config["db"]["replica"]["host"], "replica.db.com")

    def test_custom_separator_dash(self):
        """Test custom separator (-) for nested keys."""
        env_vars = {
            "SVC_API-VERSION": "2.0",
            "SVC_API-BASE-URL": "https://api.service.com",
            "SVC_AUTH-TOKEN-SECRET": "secret123",
            "SVC_AUTH-TOKEN-EXPIRY": "3600",
        }

        with patch.dict("os.environ", env_vars, clear=True):
            loader = EnvironmentLoader("SVC", separator="-")
            config = loader.load()

            self.assertEqual(config["api"]["version"], 2.0)
            self.assertEqual(config["api"]["base"]["url"], "https://api.service.com")
            self.assertEqual(config["auth"]["token"]["secret"], "secret123")
            self.assertEqual(config["auth"]["token"]["expiry"], 3600)

    def test_multi_character_separator(self):
        """Test multi-character separator (::) for nested keys."""
        env_vars = {
            "CUSTOM_DATABASE::HOST": "db.example.com",
            "CUSTOM_DATABASE::CREDENTIALS::USER": "admin",
            "CUSTOM_DATABASE::CREDENTIALS::PASS": "secret",
            "CUSTOM_FEATURES::ENABLED": "true",
        }

        with patch.dict("os.environ", env_vars, clear=True):
            loader = EnvironmentLoader("CUSTOM", separator="::")
            config = loader.load()

            self.assertEqual(config["database"]["host"], "db.example.com")
            self.assertEqual(config["database"]["credentials"]["user"], "admin")
            self.assertEqual(config["database"]["credentials"]["pass"], "secret")
            self.assertTrue(config["features"]["enabled"])

    def test_separator_not_in_values(self):
        """Test that separator in values doesn't cause issues."""
        env_vars = {
            "TEST_KEY": "value__with__separator",
            "TEST_URL": "http://example.com/path__name",
            "TEST_NESTED__KEY": "another__value__here",
        }

        with patch.dict("os.environ", env_vars, clear=True):
            loader = EnvironmentLoader("TEST", separator="__")
            config = loader.load()

            self.assertEqual(config["key"], "value__with__separator")
            self.assertEqual(config["url"], "http://example.com/path__name")
            self.assertEqual(config["nested"]["key"], "another__value__here")

    def test_deeply_nested_with_custom_separator(self):
        """Test deeply nested structures with custom separator."""
        env_vars = {
            "DEEP_LEVEL1_LEVEL2_LEVEL3_LEVEL4_VALUE": "deep_value",
            "DEEP_LEVEL1_LEVEL2_ANOTHER": "test",
            "DEEP_A_B_C_D_E_F": "six_levels",
        }

        with patch.dict("os.environ", env_vars, clear=True):
            loader = EnvironmentLoader("DEEP", separator="_")
            config = loader.load()

            self.assertEqual(
                config["level1"]["level2"]["level3"]["level4"]["value"], "deep_value"
            )
            self.assertEqual(config["level1"]["level2"]["another"], "test")
            self.assertEqual(config["a"]["b"]["c"]["d"]["e"]["f"], "six_levels")

    def test_empty_separator_single_level(self):
        """Test with empty/no nesting (single level only)."""
        env_vars = {
            "FLAT_DATABASE": "localhost:5432",
            "FLAT_APIKEY": "secret123",
            "FLAT_ENABLED": "true",
        }

        with patch.dict("os.environ", env_vars, clear=True):
            # Using a separator that won't appear treats everything as single level
            loader = EnvironmentLoader("FLAT", separator="|||")
            config = loader.load()

            self.assertEqual(config["database"], "localhost:5432")
            self.assertEqual(config["apikey"], "secret123")
            self.assertEqual(config["enabled"], True)

    def test_type_conversion_with_separator(self):
        """Test type conversion works correctly with custom separator."""
        env_vars = {
            "TYPES_NUMBERS-INTEGER": "42",
            "TYPES_NUMBERS-FLOAT": "3.14",
            "TYPES_FLAGS-ENABLED": "true",
            "TYPES_FLAGS-DISABLED": "false",
            "TYPES_STRINGS-NAME": "MyApp",
        }

        with patch.dict("os.environ", env_vars, clear=True):
            loader = EnvironmentLoader("TYPES", separator="-")
            config = loader.load()

            self.assertIsInstance(config["numbers"]["integer"], int)
            self.assertEqual(config["numbers"]["integer"], 42)

            self.assertIsInstance(config["numbers"]["float"], float)
            self.assertAlmostEqual(config["numbers"]["float"], 3.14)

            self.assertIsInstance(config["flags"]["enabled"], bool)
            self.assertTrue(config["flags"]["enabled"])
            self.assertFalse(config["flags"]["disabled"])

            self.assertIsInstance(config["strings"]["name"], str)
            self.assertEqual(config["strings"]["name"], "MyApp")

    def test_prefix_with_underscore_and_separator(self):
        """Test handling of prefix with underscore."""
        env_vars = {
            "MY_APP_CONFIG__DATABASE": "localhost",
            "MY_APP_CONFIG__PORT": "5432",
            "MY_APP_API__KEY": "abc123",  # Also matches MY_APP_ prefix
        }

        with patch.dict("os.environ", env_vars, clear=True):
            loader = EnvironmentLoader("MY_APP", separator="__")
            config = loader.load()

            self.assertEqual(config["config"]["database"], "localhost")
            self.assertEqual(config["config"]["port"], 5432)
            # MY_APP_API__KEY also matches the MY_APP prefix, so it's included
            self.assertIn("api", config)
            self.assertEqual(config["api"]["key"], "abc123")

    def test_case_preservation_in_values(self):
        """Test that case is preserved in values but not keys."""
        env_vars = {
            "CASE_DATABASE__HOST": "LocalHost",
            "CASE_DATABASE__PASSWORD": "MyP@ssW0rd",
            "CASE_API__ENDPOINT": "https://API.Example.COM/v1",
        }

        with patch.dict("os.environ", env_vars, clear=True):
            loader = EnvironmentLoader("CASE", separator="__")
            config = loader.load()

            # Keys should be lowercase
            self.assertIn("database", config)
            self.assertIn("host", config["database"])

            # Values should preserve case
            self.assertEqual(config["database"]["host"], "LocalHost")
            self.assertEqual(config["database"]["password"], "MyP@ssW0rd")
            self.assertEqual(config["api"]["endpoint"], "https://API.Example.COM/v1")

    def test_separator_at_boundaries(self):
        """Test edge cases with separator at start/end of key parts."""
        env_vars = {
            "EDGE__KEY": "value1",  # Starts with separator after prefix
            "EDGE_KEY__": "value2",  # Ends with separator
            "EDGE___KEY": "value3",  # Multiple separators
            "EDGE_NORMAL__KEY": "value4",
        }

        with patch.dict("os.environ", env_vars, clear=True):
            loader = EnvironmentLoader("EDGE", separator="__")
            config = loader.load()

            # Behavior depends on implementation
            # Typically empty parts are ignored
            self.assertIn("normal", config)
            self.assertEqual(config["normal"]["key"], "value4")

    def test_mixed_separators_in_environment(self):
        """Test that only specified separator is used for nesting."""
        env_vars = {
            "MIX_PART1__PART2": "value1",
            "MIX_OTHER_PART": "value2",  # Has _ but separator is __
            "MIX_ANOTHER__NESTED__DEEP": "value3",
        }

        with patch.dict("os.environ", env_vars, clear=True):
            loader = EnvironmentLoader("MIX", separator="__")
            config = loader.load()

            self.assertEqual(config["part1"]["part2"], "value1")
            # Single underscore is not separator, so treated as part of key
            self.assertEqual(config["other_part"], "value2")
            self.assertEqual(config["another"]["nested"]["deep"], "value3")

    def test_numeric_string_keys(self):
        """Test handling of numeric strings as keys."""
        env_vars = {
            "NUM_123_456": "value1",
            "NUM_ITEMS_0_NAME": "first",
            "NUM_ITEMS_1_NAME": "second",
            "NUM_PORTS_8080": "active",
        }

        with patch.dict("os.environ", env_vars, clear=True):
            loader = EnvironmentLoader("NUM", separator="_")
            config = loader.load()

            # Numeric keys should work
            self.assertEqual(config["123"]["456"], "value1")
            self.assertEqual(config["items"]["0"]["name"], "first")
            self.assertEqual(config["items"]["1"]["name"], "second")
            self.assertEqual(config["ports"]["8080"], "active")

    def test_special_characters_in_separator(self):
        """Test using special characters as separator."""
        # Test with pipe separator
        env_vars = {"PIPE_SECTION|KEY": "value1", "PIPE_SECTION|NESTED|DEEP": "value2"}

        with patch.dict("os.environ", env_vars, clear=True):
            loader = EnvironmentLoader("PIPE", separator="|")
            config = loader.load()

            self.assertEqual(config["section"]["key"], "value1")
            self.assertEqual(config["section"]["nested"]["deep"], "value2")

    def test_source_attribute_with_separator(self):
        """Test that source attribute includes prefix."""
        loader = EnvironmentLoader("PREFIX", separator="::")
        self.assertEqual(loader.source, "environment:PREFIX")
        self.assertEqual(loader.separator, "::")

    def test_backward_compatibility_default_separator(self):
        """Test backward compatibility with default separator."""
        env_vars = {"OLD_STYLE_DB__HOST": "localhost", "OLD_STYLE_DB__PORT": "5432"}

        with patch.dict("os.environ", env_vars, clear=True):
            # Not specifying separator should use default '__'
            loader = EnvironmentLoader("OLD_STYLE")
            config = loader.load()

            self.assertEqual(config["db"]["host"], "localhost")
            self.assertEqual(config["db"]["port"], 5432)

    def test_integration_with_config_class(self):
        """Test EnvironmentLoader with custom separator in Config class."""
        from config_stash import Config

        env_vars = {
            "MYAPP_DATABASE-HOST": "localhost",
            "MYAPP_DATABASE-PORT": "5432",
            "MYAPP_API-KEY": "secret",
        }

        with patch.dict("os.environ", env_vars, clear=True):
            # Create config with custom separator environment loader
            config = Config(
                loaders=[EnvironmentLoader("MYAPP", separator="-")],
                env="default",
                enable_ide_support=False,
            )

            # Verify nested structure is created correctly
            self.assertEqual(config.database.host, "localhost")
            self.assertEqual(config.database.port, 5432)
            self.assertEqual(config.api.key, "secret")


if __name__ == "__main__":
    unittest.main()
