import unittest
from config_stash.hook_processor import HookProcessor

class TestHookProcessor(unittest.TestCase):
    def setUp(self):
        self.processor = HookProcessor()

    def test_register_and_process_key_hook(self):
        hook = lambda x: f"hooked_{x}"
        self.processor.register_key_hook('key', hook)
        result = self.processor.process_hooks('key', 'value')
        self.assertEqual(result, 'hooked_value')

    def test_register_and_process_value_hook(self):
        hook = lambda x: f"hooked_{x}"
        self.processor.register_value_hook('value', hook)
        result = self.processor.process_hooks('key', 'value')
        self.assertEqual(result, 'hooked_value')

    def test_register_and_process_condition_hook(self):
        condition = lambda k, v: k == 'key' and v == 'value'
        hook = lambda x: f"hooked_{x}"
        self.processor.register_condition_hook(condition, hook)
        result = self.processor.process_hooks('key', 'value')
        self.assertEqual(result, 'hooked_value')

    def test_register_and_process_global_hook(self):
        hook = lambda x: f"hooked_{x}"
        self.processor.register_global_hook(hook)
        result = self.processor.process_hooks('key', 'value')
        self.assertEqual(result, 'hooked_value')

if __name__ == 'main':
    unittest.main()