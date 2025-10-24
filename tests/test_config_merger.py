import unittest

from config_stash.config_merger import ConfigMerger


class TestConfigMerger(unittest.TestCase):
    def test_merge_configs(self):
        config1 = {"key1": "value1", "nested": {"key2": "value2"}}
        config2 = {"key1": "new_value1", "nested": {"key3": "value3"}}
        configs = [(config1, ""), (config2, "")]

        # Test shallow merge (default behavior)
        merged = ConfigMerger.merge_configs(configs)
        self.assertEqual(merged["key1"], "new_value1")
        # In shallow merge, nested dict is replaced entirely
        self.assertEqual(merged["nested"], {"key3": "value3"})

    def test_deep_merge_configs(self):
        config1 = {"key1": "value1", "nested": {"key2": "value2"}}
        config2 = {"key1": "new_value1", "nested": {"key3": "value3"}}
        configs = [(config1, ""), (config2, "")]

        # Test deep merge
        merged = ConfigMerger.merge_configs(configs, deep_merge=True)
        self.assertEqual(merged["key1"], "new_value1")
        # In deep merge, nested keys are preserved
        self.assertEqual(merged["nested"]["key2"], "value2")
        self.assertEqual(merged["nested"]["key3"], "value3")


if __name__ == "__main__":
    unittest.main()
