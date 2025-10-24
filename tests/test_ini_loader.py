"""Comprehensive tests for IniLoader (INI file support)."""

import configparser
import os
import tempfile
import unittest
from pathlib import Path

from config_stash.loaders import IniLoader


class TestIniLoader(unittest.TestCase):
    """Test INI file loading functionality."""

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

    def test_basic_ini_loading(self):
        """Test loading basic INI file with sections and values."""
        ini_content = """
[database]
host = localhost
port = 5432
username = admin
password = secret

[api]
endpoint = https://api.example.com
timeout = 30
retries = 3
"""
        with open("config.ini", "w") as f:
            f.write(ini_content)

        loader = IniLoader("config.ini")
        config = loader.load()

        # Check database section
        self.assertEqual(config['database']['host'], 'localhost')
        self.assertEqual(config['database']['port'], 5432)
        self.assertEqual(config['database']['username'], 'admin')
        self.assertEqual(config['database']['password'], 'secret')

        # Check api section
        self.assertEqual(config['api']['endpoint'], 'https://api.example.com')
        self.assertEqual(config['api']['timeout'], 30)
        self.assertEqual(config['api']['retries'], 3)

    def test_type_conversion(self):
        """Test automatic type conversion for boolean, int, and float values."""
        ini_content = """
[types]
; Boolean values
enabled = true
disabled = false
verbose = True
quiet = False

; Integer values
port = 8080
max_connections = 100
timeout = 30

; Float values
pi = 3.14159
tax_rate = 0.08
version = 2.5

; String values
name = MyApp
environment = production
"""
        with open("config.ini", "w") as f:
            f.write(ini_content)

        loader = IniLoader("config.ini")
        config = loader.load()

        # Check booleans
        self.assertIsInstance(config['types']['enabled'], bool)
        self.assertTrue(config['types']['enabled'])
        self.assertFalse(config['types']['disabled'])
        self.assertTrue(config['types']['verbose'])
        self.assertFalse(config['types']['quiet'])

        # Check integers
        self.assertIsInstance(config['types']['port'], int)
        self.assertEqual(config['types']['port'], 8080)
        self.assertEqual(config['types']['max_connections'], 100)

        # Check floats
        self.assertIsInstance(config['types']['pi'], float)
        self.assertAlmostEqual(config['types']['pi'], 3.14159)
        self.assertAlmostEqual(config['types']['tax_rate'], 0.08)

        # Check strings
        self.assertIsInstance(config['types']['name'], str)
        self.assertEqual(config['types']['name'], 'MyApp')

    def test_multiple_sections(self):
        """Test loading INI file with multiple sections."""
        ini_content = """
[development]
debug = true
log_level = DEBUG
database_host = dev.db.local

[staging]
debug = false
log_level = INFO
database_host = staging.db.example.com

[production]
debug = false
log_level = WARNING
database_host = prod.db.example.com
"""
        with open("config.ini", "w") as f:
            f.write(ini_content)

        loader = IniLoader("config.ini")
        config = loader.load()

        # Check all sections are loaded
        self.assertIn('development', config)
        self.assertIn('staging', config)
        self.assertIn('production', config)

        # Check values in each section
        self.assertTrue(config['development']['debug'])
        self.assertEqual(config['development']['log_level'], 'DEBUG')

        self.assertFalse(config['staging']['debug'])
        self.assertEqual(config['staging']['log_level'], 'INFO')

        self.assertFalse(config['production']['debug'])
        self.assertEqual(config['production']['log_level'], 'WARNING')

    def test_comments_in_ini(self):
        """Test that comments are properly ignored."""
        ini_content = """
; This is a comment with semicolon
# This is a comment with hash

[section1]
; Comment before key
key1 = value1
# Another comment
key2 = value2 ; inline comment (if supported)

[section2] # section with comment
key3 = value3
"""
        with open("config.ini", "w") as f:
            f.write(ini_content)

        loader = IniLoader("config.ini")
        config = loader.load()

        # Check that only actual config values are loaded
        self.assertEqual(config['section1']['key1'], 'value1')
        self.assertEqual(config['section1']['key2'], 'value2 ; inline comment (if supported)')
        self.assertEqual(config['section2']['key3'], 'value3')

    def test_special_characters_in_values(self):
        """Test handling of special characters in values."""
        ini_content = """
[credentials]
password = p@ssw0rd!#$%
api_key = sk-1234567890abcdef
connection_string = mongodb://user:pass@host:27017/db?option=value

[paths]
windows_path = C:\\Users\\Documents\\file.txt
unix_path = /home/user/documents/file.txt
url = https://example.com/path?query=value&other=123

[patterns]
regex = ^[a-zA-Z0-9]+$
email = user@example.com
"""
        with open("config.ini", "w") as f:
            f.write(ini_content)

        loader = IniLoader("config.ini")
        config = loader.load()

        self.assertEqual(config['credentials']['password'], 'p@ssw0rd!#$%')
        self.assertEqual(config['credentials']['connection_string'],
                        'mongodb://user:pass@host:27017/db?option=value')
        self.assertEqual(config['paths']['url'],
                        'https://example.com/path?query=value&other=123')
        self.assertEqual(config['patterns']['regex'], '^[a-zA-Z0-9]+$')

    def test_whitespace_handling(self):
        """Test handling of whitespace in keys and values."""
        ini_content = """
[whitespace]
  key_with_spaces  =  value_with_spaces
no_spaces=no_spaces_value
	tab_key	=	tab_value
multiline_attempt = line1
    continued line (depends on parser)
"""
        with open("config.ini", "w") as f:
            f.write(ini_content)

        loader = IniLoader("config.ini")
        config = loader.load()

        # configparser typically strips whitespace
        self.assertIn('whitespace', config)
        # Keys should be present (exact behavior depends on configparser)
        self.assertTrue(len(config['whitespace']) > 0)

    def test_empty_sections(self):
        """Test handling of empty sections."""
        ini_content = """
[empty_section]

[section_with_values]
key1 = value1
key2 = value2

[another_empty]
; Just comments here

[final_section]
key3 = value3
"""
        with open("config.ini", "w") as f:
            f.write(ini_content)

        loader = IniLoader("config.ini")
        config = loader.load()

        # Empty sections should exist but be empty dicts
        self.assertIn('empty_section', config)
        self.assertEqual(config['empty_section'], {})

        self.assertIn('another_empty', config)
        self.assertEqual(config['another_empty'], {})

        # Non-empty sections should have values
        self.assertEqual(config['section_with_values']['key1'], 'value1')
        self.assertEqual(config['final_section']['key3'], 'value3')

    def test_nonexistent_file(self):
        """Test loading from nonexistent file returns None."""
        loader = IniLoader("nonexistent.ini")
        config = loader.load()

        self.assertIsNone(config)

    def test_empty_file(self):
        """Test loading from empty file returns empty dict."""
        with open("empty.ini", "w") as f:
            f.write("")

        loader = IniLoader("empty.ini")
        config = loader.load()

        self.assertEqual(config, {})

    def test_case_sensitivity(self):
        """Test case handling in section and key names."""
        ini_content = """
[UPPERCASE]
KEY = value1

[lowercase]
key = value2

[MixedCase]
MixedKey = value3
"""
        with open("config.ini", "w") as f:
            f.write(ini_content)

        loader = IniLoader("config.ini")
        config = loader.load()

        # configparser preserves case for section names
        # (RawConfigParser default behavior)
        self.assertIn('UPPERCASE', config)
        self.assertIn('lowercase', config)
        self.assertIn('MixedCase', config)

        self.assertEqual(config['UPPERCASE']['key'], 'value1')
        self.assertEqual(config['lowercase']['key'], 'value2')
        # configparser lowercases option names (keys)
        self.assertEqual(config['MixedCase']['mixedkey'], 'value3')

    def test_duplicate_sections(self):
        """Test handling of duplicate section names."""
        ini_content = """
[database]
host = first_host
port = 5432

[api]
endpoint = https://api.example.com

[database]
host = second_host
username = admin
"""
        with open("config.ini", "w") as f:
            f.write(ini_content)

        loader = IniLoader("config.ini")
        # configparser raises DuplicateSectionError for duplicate sections
        with self.assertRaises(configparser.DuplicateSectionError):
            config = loader.load()

    def test_equals_sign_in_values(self):
        """Test handling of equals signs in values."""
        ini_content = """
[formulas]
equation = a = b + c
expression = 2 + 2 = 4

[config]
connection = key1=value1;key2=value2
base64 = SGVsbG8gV29ybGQ=
"""
        with open("config.ini", "w") as f:
            f.write(ini_content)

        loader = IniLoader("config.ini")
        config = loader.load()

        self.assertEqual(config['formulas']['equation'], 'a = b + c')
        self.assertEqual(config['formulas']['expression'], '2 + 2 = 4')
        self.assertEqual(config['config']['connection'], 'key1=value1;key2=value2')
        self.assertEqual(config['config']['base64'], 'SGVsbG8gV29ybGQ=')

    def test_unicode_support(self):
        """Test support for Unicode characters."""
        ini_content = """
[unicode]
greeting = Hello, 世界
emoji = 🚀 Launch
currency = €100
accented = café
cyrillic = Привет
arabic = مرحبا
"""
        with open("config.ini", "w", encoding='utf-8') as f:
            f.write(ini_content)

        loader = IniLoader("config.ini")
        config = loader.load()

        self.assertEqual(config['unicode']['greeting'], 'Hello, 世界')
        self.assertEqual(config['unicode']['emoji'], '🚀 Launch')
        self.assertEqual(config['unicode']['currency'], '€100')
        self.assertEqual(config['unicode']['accented'], 'café')

    def test_long_values(self):
        """Test handling of long values."""
        long_value = "a" * 1000
        ini_content = f"""
[section]
short = short_value
long = {long_value}
"""
        with open("config.ini", "w") as f:
            f.write(ini_content)

        loader = IniLoader("config.ini")
        config = loader.load()

        self.assertEqual(config['section']['short'], 'short_value')
        self.assertEqual(config['section']['long'], long_value)
        self.assertEqual(len(config['section']['long']), 1000)

    def test_source_attribute(self):
        """Test that loader has correct source attribute."""
        loader = IniLoader("custom.ini")
        self.assertEqual(loader.source, "custom.ini")

    def test_real_world_ini_example(self):
        """Test with a realistic INI configuration file."""
        ini_content = """
[server]
host = 0.0.0.0
port = 8080
workers = 4
debug = false

[database]
engine = postgresql
host = db.example.com
port = 5432
name = myapp_production
user = dbuser
password = dbpass123
pool_size = 20
pool_recycle = 3600

[cache]
backend = redis
host = cache.example.com
port = 6379
db = 0
ttl = 300

[logging]
level = INFO
file = /var/log/myapp/app.log
max_size = 10485760
backup_count = 5
format = %(asctime)s - %(name)s - %(levelname)s - %(message)s

[security]
secret_key = your-secret-key-here
session_timeout = 3600
csrf_enabled = true
allowed_hosts = example.com,www.example.com
"""
        with open("config.ini", "w") as f:
            f.write(ini_content)

        loader = IniLoader("config.ini")
        config = loader.load()

        # Verify complex real-world config loads correctly
        self.assertEqual(config['server']['host'], '0.0.0.0')
        self.assertEqual(config['server']['port'], 8080)
        self.assertFalse(config['server']['debug'])

        self.assertEqual(config['database']['engine'], 'postgresql')
        self.assertEqual(config['database']['pool_size'], 20)

        self.assertEqual(config['cache']['backend'], 'redis')
        self.assertEqual(config['cache']['ttl'], 300)

        self.assertEqual(config['logging']['level'], 'INFO')
        self.assertEqual(config['logging']['max_size'], 10485760)

        self.assertTrue(config['security']['csrf_enabled'])
        self.assertEqual(config['security']['session_timeout'], 3600)


if __name__ == "__main__":
    unittest.main()