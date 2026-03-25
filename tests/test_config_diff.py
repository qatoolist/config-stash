"""Tests for configuration diff and drift detection."""

import unittest

from config_stash.config import Config
from config_stash.config_diff import (
    ConfigDiff,
    ConfigDiffer,
    ConfigDriftDetector,
    DiffType,
)
from config_stash.loaders import YamlLoader


class TestConfigDiff(unittest.TestCase):
    """Test configuration diff functionality."""

    def test_config_diff_created(self):
        """Test creating a ConfigDiff object."""
        diff = ConfigDiff(
            key="test_key",
            diff_type=DiffType.MODIFIED,
            old_value="old",
            new_value="new",
            path="test.path",
        )
        self.assertEqual(diff.key, "test_key")
        self.assertEqual(diff.diff_type, DiffType.MODIFIED)
        self.assertEqual(diff.old_value, "old")
        self.assertEqual(diff.new_value, "new")
        self.assertEqual(diff.path, "test.path")

    def test_config_diff_to_dict(self):
        """Test converting ConfigDiff to dictionary."""
        diff = ConfigDiff(
            key="test_key",
            diff_type=DiffType.ADDED,
            new_value="value",
            path="test.path",
        )
        diff_dict = diff.to_dict()
        self.assertEqual(diff_dict["key"], "test_key")
        self.assertEqual(diff_dict["type"], "added")
        self.assertEqual(diff_dict["new_value"], "value")

    def test_config_differ_basic(self):
        """Test basic configuration diff."""
        config1 = {"key1": "value1", "key2": "value2"}
        config2 = {"key1": "value1", "key2": "changed", "key3": "value3"}

        diffs = ConfigDiffer.diff(config1, config2)

        self.assertEqual(len(diffs), 2)
        # Check modified
        modified = [d for d in diffs if d.key == "key2"][0]
        self.assertEqual(modified.diff_type, DiffType.MODIFIED)
        self.assertEqual(modified.old_value, "value2")
        self.assertEqual(modified.new_value, "changed")
        # Check added
        added = [d for d in diffs if d.key == "key3"][0]
        self.assertEqual(added.diff_type, DiffType.ADDED)
        self.assertEqual(added.new_value, "value3")

    def test_config_differ_nested(self):
        """Test nested configuration diff."""
        config1 = {"database": {"host": "localhost", "port": 5432}}
        config2 = {"database": {"host": "remote", "port": 5432, "ssl": True}}

        diffs = ConfigDiffer.diff(config1, config2)

        self.assertEqual(len(diffs), 1)
        db_diff = diffs[0]
        self.assertEqual(db_diff.key, "database")
        self.assertEqual(len(db_diff.nested_diffs), 2)
        # Check host modified
        host_diff = [d for d in db_diff.nested_diffs if d.key == "host"][0]
        self.assertEqual(host_diff.diff_type, DiffType.MODIFIED)
        # Check ssl added
        ssl_diff = [d for d in db_diff.nested_diffs if d.key == "ssl"][0]
        self.assertEqual(ssl_diff.diff_type, DiffType.ADDED)

    def test_config_differ_removed(self):
        """Test detecting removed keys."""
        config1 = {"key1": "value1", "key2": "value2"}
        config2 = {"key1": "value1"}

        diffs = ConfigDiffer.diff(config1, config2)

        self.assertEqual(len(diffs), 1)
        removed = diffs[0]
        self.assertEqual(removed.diff_type, DiffType.REMOVED)
        self.assertEqual(removed.key, "key2")
        self.assertEqual(removed.old_value, "value2")

    def test_config_differ_summary(self):
        """Test diff summary generation."""
        config1 = {"key1": "value1", "key2": "value2", "key3": "value3"}
        config2 = {"key1": "changed", "key2": "value2", "key4": "value4"}

        diffs = ConfigDiffer.diff(config1, config2)
        summary = ConfigDiffer.diff_summary(diffs)

        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["modified"], 1)
        self.assertEqual(summary["added"], 1)
        self.assertEqual(summary["removed"], 1)

    def test_config_differ_to_json(self):
        """Test converting diff to JSON."""
        config1 = {"key1": "value1"}
        config2 = {"key1": "value2"}

        diffs = ConfigDiffer.diff(config1, config2)
        json_str = ConfigDiffer.diff_to_json(diffs)

        self.assertIn("key1", json_str)
        self.assertIn("modified", json_str)

    def test_config_instance_diff(self):
        """Test Config.diff() method."""
        import os
        import tempfile

        import yaml

        with tempfile.TemporaryDirectory() as tmpdir:
            config1_file = os.path.join(tmpdir, "config1.yaml")
            config2_file = os.path.join(tmpdir, "config2.yaml")

            with open(config1_file, "w") as f:
                yaml.dump({"database": {"host": "localhost"}}, f)
            with open(config2_file, "w") as f:
                yaml.dump({"database": {"host": "remote"}}, f)

            config1 = Config(loaders=[YamlLoader(config1_file)], enable_ide_support=False)
            config2 = Config(loaders=[YamlLoader(config2_file)], enable_ide_support=False)

            diffs = config1.diff(config2)
            self.assertGreater(len(diffs), 0)


class TestConfigDriftDetector(unittest.TestCase):
    """Test configuration drift detection."""

    def test_drift_detector_initialization(self):
        """Test initializing drift detector."""
        intended = {"key1": "value1", "key2": "value2"}
        detector = ConfigDriftDetector(intended)
        self.assertEqual(detector.intended_config, intended)

    def test_drift_detection_no_drift(self):
        """Test drift detection with no drift."""
        intended = {"key1": "value1", "key2": "value2"}
        actual = {"key1": "value1", "key2": "value2"}

        detector = ConfigDriftDetector(intended)
        drift = detector.detect_drift(actual)

        self.assertEqual(len(drift), 0)

    def test_drift_detection_with_drift(self):
        """Test drift detection with drift present."""
        intended = {"key1": "value1", "key2": "value2"}
        actual = {"key1": "changed", "key2": "value2", "key3": "added"}

        detector = ConfigDriftDetector(intended)
        drift = detector.detect_drift(actual)

        self.assertGreater(len(drift), 0)

    def test_has_drift_true(self):
        """Test has_drift returns True when drift exists."""
        intended = {"key1": "value1"}
        actual = {"key1": "different"}

        detector = ConfigDriftDetector(intended)
        self.assertTrue(detector.has_drift(actual))

    def test_has_drift_false(self):
        """Test has_drift returns False when no drift."""
        intended = {"key1": "value1"}
        actual = {"key1": "value1"}

        detector = ConfigDriftDetector(intended)
        self.assertFalse(detector.has_drift(actual))

    def test_config_instance_detect_drift(self):
        """Test Config.detect_drift() method."""
        import os
        import tempfile

        import yaml

        with tempfile.TemporaryDirectory() as tmpdir:
            intended_file = os.path.join(tmpdir, "intended.yaml")
            actual_file = os.path.join(tmpdir, "actual.yaml")

            with open(intended_file, "w") as f:
                yaml.dump({"database": {"host": "intended"}}, f)
            with open(actual_file, "w") as f:
                yaml.dump({"database": {"host": "actual"}}, f)

            intended = Config(loaders=[YamlLoader(intended_file)], enable_ide_support=False)
            actual = Config(loaders=[YamlLoader(actual_file)], enable_ide_support=False)

            drift = actual.detect_drift(intended)
            self.assertGreater(len(drift), 0)


if __name__ == "__main__":
    unittest.main()
