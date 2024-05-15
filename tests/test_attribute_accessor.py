import unittest
from config_stash.utils.lazy_loader import LazyLoader
from config_stash.attribute_accessor import AttributeAccessor

class TestAttributeAccessor(unittest.TestCase):
    def setUp(self):
        self.config = {
            'level1': {
                'level2': {
                    'key': 'value'
                }
            },
            'int_value': '42',
            'float_value': '3.14',
            'bool_true': 'true',
            'bool_false': 'false'
        }
        self.lazy_loader = LazyLoader(self.config)
        self.accessor = AttributeAccessor(self.lazy_loader)

    def test_nested_access(self):
        self.assertEqual(self.accessor.level1.level2.key, 'value')

    def test_non_existent_key(self):
        with self.assertRaises(AttributeError):
            self.accessor.non_existent

    def test_type_casting(self):
        self.assertEqual(self.accessor.int_value, 42)
        self.assertEqual(self.accessor.float_value, 3.14)
        self.assertEqual(self.accessor.bool_true, True)
        self.assertEqual(self.accessor.bool_false, False)

if __name__ == '__main__':
    unittest.main()