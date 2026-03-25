"""Comprehensive tests for EnvFileLoader (.env file support)."""

import os
import tempfile
import unittest
from pathlib import Path

from config_stash.loaders import EnvFileLoader


class TestEnvFileLoader(unittest.TestCase):
    """Test .env file loading functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.temp_dir)

    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_dir)
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_basic_env_file_loading(self):
        """Test loading basic key-value pairs from .env file."""
        env_content = """
DATABASE_HOST=localhost
DATABASE_PORT=5432
API_KEY=secret123
DEBUG=true
"""
        with open(".env", "w") as f:
            f.write(env_content)

        loader = EnvFileLoader(".env")
        config = loader.load()

        self.assertEqual(config["DATABASE_HOST"], "localhost")
        self.assertEqual(config["DATABASE_PORT"], 5432)
        self.assertEqual(config["API_KEY"], "secret123")
        self.assertEqual(config["DEBUG"], True)

    def test_type_conversion(self):
        """Test automatic type conversion for boolean, int, and float values."""
        env_content = """
# Boolean values
FEATURE_ENABLED=true
MAINTENANCE_MODE=false
DEBUG=True
VERBOSE=False

# Integer values
PORT=8080
MAX_CONNECTIONS=100
TIMEOUT=30

# Float values
PI=3.14159
TAX_RATE=0.08
VERSION=2.5

# String values
NAME=MyApp
ENVIRONMENT=production
"""
        with open(".env", "w") as f:
            f.write(env_content)

        loader = EnvFileLoader(".env")
        config = loader.load()

        # Check booleans
        self.assertIsInstance(config["FEATURE_ENABLED"], bool)
        self.assertTrue(config["FEATURE_ENABLED"])
        self.assertFalse(config["MAINTENANCE_MODE"])
        self.assertTrue(config["DEBUG"])
        self.assertFalse(config["VERBOSE"])

        # Check integers
        self.assertIsInstance(config["PORT"], int)
        self.assertEqual(config["PORT"], 8080)
        self.assertEqual(config["MAX_CONNECTIONS"], 100)

        # Check floats
        self.assertIsInstance(config["PI"], float)
        self.assertAlmostEqual(config["PI"], 3.14159)
        self.assertAlmostEqual(config["TAX_RATE"], 0.08)

        # Check strings
        self.assertIsInstance(config["NAME"], str)
        self.assertEqual(config["NAME"], "MyApp")

    def test_nested_keys_with_dot_notation(self):
        """Test support for nested configuration using dot notation."""
        env_content = """
database.host=localhost
database.port=5432
database.credentials.username=admin
database.credentials.password=secret
api.endpoint=https://api.example.com
api.timeout=30
api.retry.max_attempts=3
api.retry.delay=1000
"""
        with open(".env", "w") as f:
            f.write(env_content)

        loader = EnvFileLoader(".env")
        config = loader.load()

        # Check nested structure
        self.assertEqual(config["database"]["host"], "localhost")
        self.assertEqual(config["database"]["port"], 5432)
        self.assertEqual(config["database"]["credentials"]["username"], "admin")
        self.assertEqual(config["database"]["credentials"]["password"], "secret")
        self.assertEqual(config["api"]["endpoint"], "https://api.example.com")
        self.assertEqual(config["api"]["timeout"], 30)
        self.assertEqual(config["api"]["retry"]["max_attempts"], 3)
        self.assertEqual(config["api"]["retry"]["delay"], 1000)

    def test_quoted_values(self):
        """Test handling of quoted values."""
        env_content = """
SINGLE_QUOTED='value with spaces'
DOUBLE_QUOTED="another value with spaces"
MIXED_QUOTES="it's a value"
NO_QUOTES=no_quotes_needed
EMPTY_QUOTES=""
URL="https://example.com/path?query=value&other=123"
JSON='{"key": "value", "number": 42}'
"""
        with open(".env", "w") as f:
            f.write(env_content)

        loader = EnvFileLoader(".env")
        config = loader.load()

        self.assertEqual(config["SINGLE_QUOTED"], "value with spaces")
        self.assertEqual(config["DOUBLE_QUOTED"], "another value with spaces")
        self.assertEqual(config["MIXED_QUOTES"], "it's a value")
        self.assertEqual(config["NO_QUOTES"], "no_quotes_needed")
        self.assertEqual(config["EMPTY_QUOTES"], "")
        self.assertEqual(config["URL"], "https://example.com/path?query=value&other=123")
        self.assertEqual(config["JSON"], '{"key": "value", "number": 42}')

    def test_escape_sequences(self):
        """Test handling of escape sequences."""
        env_content = """
NEWLINE_TEXT=line1\\nline2\\nline3
TAB_TEXT=col1\\tcol2\\tcol3
MIXED_ESCAPE=Hello\\nWorld\\t!
PATH_WITH_BACKSLASH=C:\\\\Users\\\\Documents
"""
        with open(".env", "w") as f:
            f.write(env_content)

        loader = EnvFileLoader(".env")
        config = loader.load()

        self.assertEqual(config["NEWLINE_TEXT"], "line1\nline2\nline3")
        self.assertEqual(config["TAB_TEXT"], "col1\tcol2\tcol3")
        self.assertEqual(config["MIXED_ESCAPE"], "Hello\nWorld\t!")
        # Double backslash becomes single after one level of escaping
        self.assertIn("Users", config["PATH_WITH_BACKSLASH"])

    def test_comments_and_empty_lines(self):
        """Test that comments and empty lines are ignored."""
        env_content = """
# This is a comment
DATABASE_HOST=localhost

# Another comment
DATABASE_PORT=5432

   # Indented comment

# Comment with = sign in it = test
API_KEY=secret

# End comment
"""
        with open(".env", "w") as f:
            f.write(env_content)

        loader = EnvFileLoader(".env")
        config = loader.load()

        # Only actual config values should be loaded
        self.assertEqual(len(config), 3)
        self.assertEqual(config["DATABASE_HOST"], "localhost")
        self.assertEqual(config["DATABASE_PORT"], 5432)
        self.assertEqual(config["API_KEY"], "secret")

    def test_special_characters_in_values(self):
        """Test handling of special characters in values."""
        env_content = """
PASSWORD=p@ssw0rd!#$%
EMAIL=user@example.com
CONNECTION_STRING=mongodb://user:pass@host:27017/db?option=value
REGEX_PATTERN=^[a-zA-Z0-9]+$
MATH_EXPRESSION=2+2=4
"""
        with open(".env", "w") as f:
            f.write(env_content)

        loader = EnvFileLoader(".env")
        config = loader.load()

        self.assertEqual(config["PASSWORD"], "p@ssw0rd!#$%")
        self.assertEqual(config["EMAIL"], "user@example.com")
        self.assertEqual(
            config["CONNECTION_STRING"], "mongodb://user:pass@host:27017/db?option=value"
        )
        self.assertEqual(config["REGEX_PATTERN"], "^[a-zA-Z0-9]+$")
        self.assertEqual(config["MATH_EXPRESSION"], "2+2=4")

    def test_nonexistent_file(self):
        """Test loading from nonexistent file returns None."""
        loader = EnvFileLoader("nonexistent.env")
        config = loader.load()

        self.assertIsNone(config)

    def test_empty_file(self):
        """Test loading from empty file returns empty dict."""
        with open(".env", "w") as f:
            f.write("")

        loader = EnvFileLoader(".env")
        config = loader.load()

        self.assertEqual(config, {})

    def test_malformed_lines(self):
        """Test handling of malformed lines in .env file."""
        env_content = """
VALID_KEY=valid_value
InvalidLine
=NO_KEY
NO_VALUE=
ANOTHER_VALID=test
KEY WITH SPACES=should_not_work
"""
        with open(".env", "w") as f:
            f.write(env_content)

        loader = EnvFileLoader(".env")
        config = loader.load()

        # Valid keys should be loaded
        self.assertEqual(config["VALID_KEY"], "valid_value")
        self.assertEqual(config["ANOTHER_VALID"], "test")
        # Empty value should be empty string
        self.assertEqual(config["NO_VALUE"], "")

    def test_multiple_equals_signs(self):
        """Test handling of multiple equals signs in a line."""
        env_content = """
EQUATION=a=b+c
URL=https://example.com?param1=value1&param2=value2
BASE64=SGVsbG8gV29ybGQ=
CONFIG=key1=val1;key2=val2
"""
        with open(".env", "w") as f:
            f.write(env_content)

        loader = EnvFileLoader(".env")
        config = loader.load()

        # Everything after first = should be the value
        self.assertEqual(config["EQUATION"], "a=b+c")
        self.assertEqual(config["URL"], "https://example.com?param1=value1&param2=value2")
        self.assertEqual(config["BASE64"], "SGVsbG8gV29ybGQ=")
        self.assertEqual(config["CONFIG"], "key1=val1;key2=val2")

    def test_whitespace_handling(self):
        """Test handling of whitespace around keys and values."""
        env_content = """
  KEY_WITH_SPACES  =  value_with_spaces
NO_SPACES=no_spaces
	TAB_KEY	=	tab_value
TRAILING_SPACE=value
   LEADING_SPACE=   value
"""
        with open(".env", "w") as f:
            f.write(env_content)

        loader = EnvFileLoader(".env")
        config = loader.load()

        # Keys and values should be stripped
        self.assertEqual(config["KEY_WITH_SPACES"], "value_with_spaces")
        self.assertEqual(config["NO_SPACES"], "no_spaces")
        self.assertEqual(config["TAB_KEY"], "tab_value")
        self.assertEqual(config["TRAILING_SPACE"], "value")
        self.assertEqual(config["LEADING_SPACE"], "value")

    def test_unicode_support(self):
        """Test support for Unicode characters."""
        env_content = """
GREETING=Hello, 世界
EMOJI=🚀 Rocket Launch
CURRENCY=€100
SPECIAL=café
"""
        with open(".env", "w", encoding="utf-8") as f:
            f.write(env_content)

        loader = EnvFileLoader(".env")
        config = loader.load()

        self.assertEqual(config["GREETING"], "Hello, 世界")
        self.assertEqual(config["EMOJI"], "🚀 Rocket Launch")
        self.assertEqual(config["CURRENCY"], "€100")
        self.assertEqual(config["SPECIAL"], "café")

    def test_custom_env_file_path(self):
        """Test loading from custom .env file paths."""
        # Test with different file names
        for env_file in [".env.local", ".env.production", "config.env", "settings.env"]:
            env_content = f"FILE={env_file}\nVALUE=test"
            with open(env_file, "w") as f:
                f.write(env_content)

            loader = EnvFileLoader(env_file)
            config = loader.load()

            self.assertEqual(config["FILE"], env_file)
            self.assertEqual(config["VALUE"], "test")

    def test_deeply_nested_structures(self):
        """Test creation of deeply nested structures."""
        env_content = """
app.server.host=localhost
app.server.port=8080
app.server.ssl.enabled=true
app.server.ssl.cert.path=/etc/ssl/cert.pem
app.server.ssl.cert.key=/etc/ssl/key.pem
app.database.primary.host=db1.example.com
app.database.primary.port=5432
app.database.replica.host=db2.example.com
app.database.replica.port=5433
"""
        with open(".env", "w") as f:
            f.write(env_content)

        loader = EnvFileLoader(".env")
        config = loader.load()

        # Verify deep nesting
        self.assertEqual(config["app"]["server"]["host"], "localhost")
        self.assertEqual(config["app"]["server"]["ssl"]["enabled"], True)
        self.assertEqual(config["app"]["server"]["ssl"]["cert"]["path"], "/etc/ssl/cert.pem")
        self.assertEqual(config["app"]["database"]["primary"]["host"], "db1.example.com")
        self.assertEqual(config["app"]["database"]["replica"]["port"], 5433)

    def test_source_attribute(self):
        """Test that loader has correct source attribute."""
        loader = EnvFileLoader("custom.env")
        self.assertEqual(loader.source, "custom.env")


if __name__ == "__main__":
    unittest.main()
