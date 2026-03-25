"""Tests for configuration versioning."""

import json
import os
import shutil
import tempfile
import time
import unittest

from config_stash.config import Config
from config_stash.config_versioning import (
    ConfigVersion,
    ConfigVersionManager,
)
from config_stash.loaders import YamlLoader


class TestConfigVersion(unittest.TestCase):
    """Test configuration version class."""
# pyright: reportOptionalSubscript=false, reportOptionalMemberAccess=false
# pyright: reportArgumentType=false, reportPossiblyUnboundVariable=false
# pyright: reportAttributeAccessIssue=false, reportCallIssue=false
# pyright: reportMissingImports=false

    def test_version_initialization(self):
        """Test initializing version."""
        config_dict = {"key": "value"}
        version = ConfigVersion("v1", config_dict)
        self.assertEqual(version.version_id, "v1")
        self.assertEqual(version.config_dict, config_dict)
        self.assertIsNotNone(version.timestamp)

    def test_version_to_dict(self):
        """Test converting version to dictionary."""
        config_dict = {"key": "value"}
        version = ConfigVersion("v1", config_dict, metadata={"author": "test"})
        version_dict = version.to_dict()
        self.assertEqual(version_dict["version_id"], "v1")
        self.assertEqual(version_dict["config"], config_dict)
        self.assertEqual(version_dict["metadata"]["author"], "test")

    def test_version_from_dict(self):
        """Test creating version from dictionary."""
        data = {
            "version_id": "v1",
            "config": {"key": "value"},
            "timestamp": time.time(),
            "metadata": {"author": "test"},
        }
        version = ConfigVersion.from_dict(data)
        self.assertEqual(version.version_id, "v1")
        self.assertEqual(version.config_dict, {"key": "value"})


class TestConfigVersionManager(unittest.TestCase):
    """Test configuration version manager."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.version_manager = ConfigVersionManager(storage_path=self.temp_dir)

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_version_manager_initialization(self):
        """Test initializing version manager."""
        self.assertIsNotNone(self.version_manager.storage_path)
        self.assertTrue(os.path.exists(self.version_manager.storage_path))

    def test_save_version(self):
        """Test saving version."""
        config_dict = {"key": "value"}
        version = self.version_manager.save_version(config_dict)
        self.assertIsNotNone(version)
        self.assertIsNotNone(version.version_id)
        self.assertEqual(version.config_dict, config_dict)

    def test_get_version(self):
        """Test getting version by ID."""
        config_dict = {"key": "value"}
        version = self.version_manager.save_version(config_dict)
        retrieved = self.version_manager.get_version(version.version_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.version_id, version.version_id)

    def test_list_versions(self):
        """Test listing versions."""
        config1 = {"key1": "value1"}
        config2 = {"key2": "value2"}
        self.version_manager.save_version(config1)
        time.sleep(0.01)  # Small delay to ensure different timestamps
        self.version_manager.save_version(config2)

        versions = self.version_manager.list_versions()
        self.assertEqual(len(versions), 2)
        # Should be sorted by timestamp (newest first)
        self.assertEqual(versions[0].config_dict, config2)

    def test_get_latest_version(self):
        """Test getting latest version."""
        config1 = {"key1": "value1"}
        config2 = {"key2": "value2"}
        self.version_manager.save_version(config1)
        time.sleep(0.01)
        self.version_manager.save_version(config2)

        latest = self.version_manager.get_latest_version()
        self.assertIsNotNone(latest)
        self.assertEqual(latest.config_dict, config2)

    def test_rollback(self):
        """Test rolling back to version."""
        config1 = {"key": "value1"}
        config2 = {"key": "value2"}
        version1 = self.version_manager.save_version(config1)
        self.version_manager.save_version(config2)

        rolled_back = self.version_manager.rollback(version1.version_id)
        self.assertEqual(rolled_back, config1)

    def test_rollback_invalid_version(self):
        """Test rolling back to non-existent version."""
        with self.assertRaises(ValueError):
            self.version_manager.rollback("nonexistent")

    def test_diff_versions(self):
        """Test diffing versions."""
        config1 = {"key1": "value1", "key2": "value2"}
        config2 = {"key1": "changed", "key2": "value2", "key3": "value3"}

        version1 = self.version_manager.save_version(config1)
        version2 = self.version_manager.save_version(config2)

        diffs = self.version_manager.diff_versions(version1.version_id, version2.version_id)
        self.assertGreater(len(diffs), 0)


class TestConfigVersioningIntegration(unittest.TestCase):
    """Test versioning integration with Config."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.version_manager = ConfigVersionManager(storage_path=self.temp_dir)

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_config_enable_versioning(self):
        """Test enabling versioning on Config."""
        config = Config(env="test", loaders=[], enable_ide_support=False)
        manager = config.enable_versioning(storage_path=self.temp_dir)
        self.assertIsNotNone(manager)
        self.assertIsInstance(manager, ConfigVersionManager)

    def test_config_save_version(self):
        """Test saving version from Config."""
        config = Config(env="test", loaders=[], enable_ide_support=False)
        config.enable_versioning(storage_path=self.temp_dir)
        version = config.save_version(metadata={"author": "test"})
        self.assertIsNotNone(version)

    def test_config_get_version(self):
        """Test getting version from Config."""
        config = Config(env="test", loaders=[], enable_ide_support=False)
        config.enable_versioning(storage_path=self.temp_dir)
        version = config.save_version()
        retrieved = config.get_version(version.version_id)
        self.assertIsNotNone(retrieved)

    def test_config_rollback_to_version(self):
        """Test rolling back Config to version."""
        import tempfile

        import yaml

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = os.path.join(tmpdir, "config.yaml")
            with open(config_file, "w") as f:
                yaml.dump({"database": {"host": "localhost"}}, f)

            config = Config(
                loaders=[YamlLoader(config_file)],
                enable_ide_support=False,
            )
            config.enable_versioning(storage_path=self.temp_dir)

            # Save initial version
            version1 = config.save_version()
            initial_host = config.database.host

            # Modify config
            config.set("database.host", "remote")
            config.save_version()

            # Rollback
            config.rollback_to_version(version1.version_id)
            self.assertEqual(config.database.host, initial_host)


if __name__ == "__main__":
    unittest.main()
