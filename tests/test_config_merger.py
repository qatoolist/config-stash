import unittest
from config_stash.config_merger import ConfigMerger

class TestConfigMerger(unittest.TestCase):
    def test_merge_configs(self):
        config1 = {'key1': 'value1', 'nested': {'key2': 'value2'}}
        config2 = {'key1': 'new_value1', 'nested': {'key3': 'value3'}}
        configs = [(config1, ''), (config2, '')]
        merged = ConfigMerger.merge_configs(configs)
        self.assertEqual(merged['key1'], 'new_value1')
        self.assertEqual(merged['nested']['key2'], 'value2')
        self.assertEqual(merged['nested']['key3'], 'value3')

if __name__ == '__main__':
    unittest.main()