import unittest
from click.testing import CliRunner
from config_stash.cli import cli

class TestCLI(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    def test_load_command(self):
        result = self.runner.invoke(cli, ['load', 'development'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('Merged configuration', result.output)

    def test_get_command(self):
        result = self.runner.invoke(cli, ['get', 'development', 'some_key'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn('value', result.output)

if __name__ == '__main__':
    unittest.main()