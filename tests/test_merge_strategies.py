"""Tests for advanced merging strategies."""

import unittest
from typing import Any, Dict

from config_stash.merge_strategies import (
    AdvancedConfigMerger,
    MergeStrategy,
)


class TestMergeStrategy(unittest.TestCase):
    """Test merge strategy enum."""

    def test_merge_strategy_values(self):
        """Test merge strategy enum values."""
        self.assertEqual(MergeStrategy.REPLACE.value, "replace")
        self.assertEqual(MergeStrategy.MERGE.value, "merge")
        self.assertEqual(MergeStrategy.APPEND.value, "append")
        self.assertEqual(MergeStrategy.PREPEND.value, "prepend")
        self.assertEqual(MergeStrategy.INTERSECTION.value, "intersection")
        self.assertEqual(MergeStrategy.UNION.value, "union")


class TestAdvancedConfigMerger(unittest.TestCase):
    """Test advanced configuration merger."""

    def test_merger_initialization(self):
        """Test initializing merger."""
        merger = AdvancedConfigMerger()
        self.assertEqual(merger.default_strategy, MergeStrategy.MERGE)

    def test_merger_set_strategy(self):
        """Test setting strategy for key path."""
        merger = AdvancedConfigMerger()
        merger.set_strategy("database", MergeStrategy.REPLACE)
        self.assertEqual(merger.strategy_map["database"], MergeStrategy.REPLACE)

    def test_merger_replace_strategy(self):
        """Test REPLACE merge strategy."""
        merger = AdvancedConfigMerger(MergeStrategy.REPLACE)
        base = {"key": "value1"}
        new = {"key": "value2"}
        result = merger.merge(base, new)
        self.assertEqual(result["key"], "value2")

    def test_merger_merge_strategy(self):
        """Test MERGE merge strategy."""
        merger = AdvancedConfigMerger(MergeStrategy.MERGE)
        base: Dict[str, Any] = {"database": {"host": "localhost", "port": 5432}}
        new: Dict[str, Any] = {"database": {"port": 3306, "ssl": True}}
        result = merger.merge(base, new)
        self.assertEqual(result["database"]["host"], "localhost")
        self.assertEqual(result["database"]["port"], 3306)
        self.assertEqual(result["database"]["ssl"], True)

    def test_merger_append_strategy(self):
        """Test APPEND merge strategy."""
        merger = AdvancedConfigMerger(MergeStrategy.APPEND)
        base = {"list": [1, 2, 3]}
        new = {"list": [4, 5]}
        result = merger.merge(base, new)
        self.assertEqual(result["list"], [1, 2, 3, 4, 5])

    def test_merger_prepend_strategy(self):
        """Test PREPEND merge strategy."""
        merger = AdvancedConfigMerger(MergeStrategy.PREPEND)
        base = {"list": [1, 2, 3]}
        new = {"list": [4, 5]}
        result = merger.merge(base, new)
        self.assertEqual(result["list"], [4, 5, 1, 2, 3])

    def test_merger_intersection_strategy(self):
        """Test INTERSECTION merge strategy."""
        merger = AdvancedConfigMerger(MergeStrategy.INTERSECTION)
        base = {"key1": "value1", "key2": "value2", "key3": "value3"}
        new = {"key2": "changed", "key3": "value3", "key4": "value4"}
        result = merger.merge(base, new)
        self.assertIn("key2", result)
        self.assertIn("key3", result)
        self.assertNotIn("key1", result)
        self.assertNotIn("key4", result)

    def test_merger_union_strategy(self):
        """Test UNION merge strategy."""
        merger = AdvancedConfigMerger(MergeStrategy.UNION)
        base = {"key1": "value1", "key2": "value2"}
        new = {"key2": "changed", "key3": "value3"}
        result = merger.merge(base, new)
        self.assertEqual(result["key1"], "value1")
        self.assertEqual(result["key2"], "changed")
        self.assertEqual(result["key3"], "value3")

    def test_merger_key_specific_strategy(self):
        """Test setting strategy for specific key."""
        merger = AdvancedConfigMerger(MergeStrategy.MERGE)
        merger.set_strategy("database", MergeStrategy.REPLACE)
        merger.set_strategy("app.debug", MergeStrategy.REPLACE)

        base: Dict[str, Any] = {
            "database": {"host": "localhost", "port": 5432},
            "app": {"debug": True, "name": "test"},
        }
        new: Dict[str, Any] = {
            "database": {"host": "remote"},
            "app": {"debug": False},
        }

        result = merger.merge(base, new)
        # database should be replaced entirely
        self.assertEqual(result["database"], {"host": "remote"})
        # app.debug should be replaced, but app.name should remain
        self.assertEqual(result["app"]["debug"], False)
        self.assertEqual(result["app"]["name"], "test")

    def test_merger_strategy_inheritance(self):
        """Test that strategies inherit from parent paths."""
        merger = AdvancedConfigMerger(MergeStrategy.MERGE)
        merger.set_strategy("app", MergeStrategy.REPLACE)

        base = {"app": {"feature1": True, "feature2": False}}
        new = {"app": {"feature1": False}}

        result = merger.merge(base, new)
        # app should be replaced entirely
        self.assertEqual(result["app"], {"feature1": False})


if __name__ == "__main__":
    unittest.main()
