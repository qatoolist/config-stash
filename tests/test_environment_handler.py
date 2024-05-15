import unittest
from config_stash.environment_handler import EnvironmentHandler

class TestEnvironmentHandler(unittest.TestCase):
    def setUp(self):
        self.config = {
            'default': {'key': 'default_value'},
            'production': {'key': 'prod_value', 'new_key': 'new_value'}
        }
        self.handler = EnvironmentHandler('production', self.config)

    def test_get_env_config(self):
        env_config = self.handler.get_env_config()
        self.assertEqual(env_config['key'], 'prod_value')
        self.assertEqual(env_config['new_key'], 'new_value')
        self.assertEqual(env_config['default'], {'key': 'default_value'})

if __name__ == '__main__':
    unittest.main()