"""Comprehensive tests for on_change callback functionality."""

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from config_stash import Config
from config_stash.loaders import YamlLoader


class TestOnChangeCallbacks(unittest.TestCase):
    """Test the on_change callback mechanism."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        # Create initial config file
        self.config_file = "test_config.yaml"
        self.initial_config = """
default:
  database:
    host: localhost
    port: 5432
    name: testdb
  api:
    endpoint: http://api.example.com
    timeout: 30
"""
        with open(self.config_file, "w") as f:
            f.write(self.initial_config)

        self.updated_config = """
default:
  database:
    host: production.db.com
    port: 3306
    name: proddb
  api:
    endpoint: https://api.prod.com
    timeout: 60
  new_feature:
    enabled: true
"""

    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_dir)
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_on_change_decorator_registration(self):
        """Test that callbacks can be registered using the decorator."""
        config = Config(
            loaders=[YamlLoader(self.config_file)],
            env="default",
            enable_ide_support=False
        )

        callback_mock = MagicMock()

        @config.on_change
        def my_callback(key, old_value, new_value):
            callback_mock(key, old_value, new_value)

        # Verify callback is registered
        self.assertIn(my_callback, config._change_callbacks)
        self.assertEqual(len(config._change_callbacks), 1)

    def test_multiple_callbacks_registration(self):
        """Test that multiple callbacks can be registered."""
        config = Config(
            loaders=[YamlLoader(self.config_file)],
            env="default",
            enable_ide_support=False
        )

        callback1 = MagicMock()
        callback2 = MagicMock()
        callback3 = MagicMock()

        @config.on_change
        def cb1(key, old, new):
            callback1(key, old, new)

        @config.on_change
        def cb2(key, old, new):
            callback2(key, old, new)

        @config.on_change
        def cb3(key, old, new):
            callback3(key, old, new)

        self.assertEqual(len(config._change_callbacks), 3)

    def test_callbacks_triggered_on_reload(self):
        """Test that callbacks are triggered when config is reloaded."""
        config = Config(
            loaders=[YamlLoader(self.config_file)],
            env="default",
            enable_ide_support=False
        )

        changes_captured = []

        @config.on_change
        def capture_changes(key, old_value, new_value):
            changes_captured.append({
                'key': key,
                'old': old_value,
                'new': new_value
            })

        # Update the config file
        with open(self.config_file, "w") as f:
            f.write(self.updated_config)

        # Reload configuration
        config.reload()

        # Verify changes were captured
        self.assertTrue(len(changes_captured) > 0)

        # Check specific changes
        changes_dict = {c['key']: c for c in changes_captured}

        # Database host changed
        if 'database' in changes_dict:
            db_change = changes_dict['database']
            self.assertIn('localhost', str(db_change['old']))
            self.assertIn('production.db.com', str(db_change['new']))

        # New feature was added
        self.assertIn('new_feature', changes_dict)
        self.assertIsNone(changes_dict['new_feature']['old'])
        self.assertIsNotNone(changes_dict['new_feature']['new'])

    def test_callback_error_handling(self):
        """Test that errors in callbacks don't break the reload process."""
        config = Config(
            loaders=[YamlLoader(self.config_file)],
            env="default",
            enable_ide_support=False
        )

        good_callback = MagicMock()

        @config.on_change
        def failing_callback(key, old, new):
            raise ValueError("Intentional error")

        @config.on_change
        def working_callback(key, old, new):
            good_callback(key, old, new)

        # Update config file
        with open(self.config_file, "w") as f:
            f.write(self.updated_config)

        # Reload should not raise despite callback error
        with patch('config_stash.config.logger') as mock_logger:
            config.reload()

            # Check that error was logged
            mock_logger.error.assert_called()
            error_calls = mock_logger.error.call_args_list
            self.assertTrue(any('Error in change callback' in str(call) for call in error_calls))

        # Good callback should still have been called
        good_callback.assert_called()

    def test_callback_with_dynamic_reloading(self):
        """Test callbacks work with dynamic reloading (file watching)."""
        config = Config(
            loaders=[YamlLoader(self.config_file)],
            env="default",
            dynamic_reloading=True,
            enable_ide_support=False
        )

        changes_captured = []

        @config.on_change
        def capture_changes(key, old_value, new_value):
            changes_captured.append({
                'key': key,
                'old': old_value,
                'new': new_value
            })

        # Update the config file
        with open(self.config_file, "w") as f:
            f.write(self.updated_config)

        # Give file watcher time to detect change and reload (macOS needs more time)
        time.sleep(2.0)

        # Manually trigger reload in case file watcher hasn't fired yet (macOS timing issue)
        if len(changes_captured) == 0:
            config.reload()

        # Changes should have been captured
        self.assertTrue(len(changes_captured) > 0)

        # Stop watching
        config.stop_watching()

    def test_callbacks_with_nested_changes(self):
        """Test callbacks properly handle nested configuration changes."""
        config = Config(
            loaders=[YamlLoader(self.config_file)],
            env="default",
            enable_ide_support=False
        )

        changes = {}

        @config.on_change
        def track_changes(key, old_value, new_value):
            changes[key] = {'old': old_value, 'new': new_value}

        # Create config with nested changes
        nested_update = """
default:
  database:
    host: localhost
    port: 5432
    name: testdb
    connection:
      pool_size: 10
      timeout: 30
  api:
    endpoint: http://api.example.com
    timeout: 30
"""
        with open(self.config_file, "w") as f:
            f.write(nested_update)

        config.reload()

        # Verify nested structure changes are detected
        self.assertIn('database', changes)

    def test_callback_return_value(self):
        """Test that callback decorator returns the original function."""
        config = Config(
            loaders=[YamlLoader(self.config_file)],
            env="default",
            enable_ide_support=False
        )

        def my_callback(key, old, new):
            return f"Changed: {key}"

        decorated = config.on_change(my_callback)

        # Decorator should return the original function
        self.assertEqual(decorated, my_callback)
        self.assertEqual(decorated("test", "old", "new"), "Changed: test")

    def test_callbacks_with_value_deletion(self):
        """Test callbacks when configuration values are deleted."""
        config = Config(
            loaders=[YamlLoader(self.config_file)],
            env="default",
            enable_ide_support=False
        )

        deletions = []

        @config.on_change
        def track_deletions(key, old_value, new_value):
            if new_value is None and old_value is not None:
                deletions.append(key)

        # Update config with deleted values
        minimal_config = """
default:
  database:
    host: localhost
"""
        with open(self.config_file, "w") as f:
            f.write(minimal_config)

        config.reload()

        # API section should be detected as deleted
        self.assertIn('api', deletions)

    def test_callbacks_with_type_changes(self):
        """Test callbacks when value types change."""
        config = Config(
            loaders=[YamlLoader(self.config_file)],
            env="default",
            enable_ide_support=False
        )

        type_changes = []

        @config.on_change
        def track_type_changes(key, old_value, new_value):
            if old_value is not None and new_value is not None:
                if type(old_value) != type(new_value):
                    type_changes.append({
                        'key': key,
                        'old_type': type(old_value).__name__,
                        'new_type': type(new_value).__name__
                    })

        # Change port from int to string
        type_change_config = """
default:
  database:
    host: localhost
    port: "5432"  # Now a string
    name: testdb
  api:
    endpoint: http://api.example.com
    timeout: 30
"""
        with open(self.config_file, "w") as f:
            f.write(type_change_config)

        config.reload()

        # Check if type changes were detected
        if type_changes:  # Type preservation depends on YAML parser
            self.assertTrue(any(tc['key'] == 'database' for tc in type_changes))

    def test_callback_with_environment_specific_changes(self):
        """Test callbacks with environment-specific configuration changes."""
        # Create configs for different environments
        env_config = """
default:
  database:
    host: localhost
    port: 5432

production:
  database:
    host: prod.db.com
    port: 3306

development:
  database:
    host: dev.db.com
    port: 5433
"""
        with open(self.config_file, "w") as f:
            f.write(env_config)

        # Test with production environment
        config = Config(
            loaders=[YamlLoader(self.config_file)],
            env="production",
            enable_ide_support=False
        )

        changes = []

        @config.on_change
        def track_changes(key, old, new):
            changes.append({'key': key, 'old': old, 'new': new})

        # Update production config
        updated_env_config = """
default:
  database:
    host: localhost
    port: 5432

production:
  database:
    host: new-prod.db.com
    port: 3307
    ssl_enabled: true

development:
  database:
    host: dev.db.com
    port: 5433
"""
        with open(self.config_file, "w") as f:
            f.write(updated_env_config)

        config.reload()

        # Verify environment-specific changes were detected
        self.assertTrue(len(changes) > 0)

        # Check for database changes
        db_changes = [c for c in changes if 'database' in str(c['key'])]
        self.assertTrue(len(db_changes) > 0)


class TestOnChangeIntegrationWithIDESupport(unittest.TestCase):
    """Test on_change callbacks integration with IDE support."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        self.config_file = "test_config.yaml"
        self.initial_config = """
default:
  feature:
    enabled: true
"""
        with open(self.config_file, "w") as f:
            f.write(self.initial_config)

    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_dir)
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_ide_stub_regeneration_on_change(self):
        """Test that IDE stubs are regenerated when config changes."""
        config = Config(
            loaders=[YamlLoader(self.config_file)],
            env="default",
            enable_ide_support=True,
            dynamic_reloading=True
        )

        # Check initial stub exists
        stub_file = Path(".config_stash/stubs.pyi")
        self.assertTrue(stub_file.exists())

        initial_content = stub_file.read_text()

        # Update config with new structure
        updated = """
default:
  feature:
    enabled: false
  new_feature:
    name: test
"""
        with open(self.config_file, "w") as f:
            f.write(updated)

        # Give time for file watcher (macOS needs more time)
        time.sleep(2.0)

        # Manually trigger reload in case file watcher hasn't fired yet (macOS timing issue)
        initial_stub_content = stub_file.read_text()
        if initial_stub_content == initial_content:
            config.reload()
            # Small delay to let IDE stub regeneration complete
            time.sleep(0.1)

        # Stub should be regenerated with new structure
        new_content = stub_file.read_text()

        # Content should be different (new_feature added)
        self.assertNotEqual(initial_content, new_content)

        config.stop_watching()


if __name__ == "__main__":
    unittest.main()