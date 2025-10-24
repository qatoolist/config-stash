import unittest
from unittest.mock import Mock

from config_stash.config import Config
from config_stash.config_extender import ConfigExtender


class TestConfigExtender(unittest.TestCase):
    def setUp(self):
        self.config = Mock(spec=Config)
        self.config.merged_config = {}
        self.config.env = "default"
        self.extender = ConfigExtender(self.config)

    def test_extend(self):
        mock_loader = Mock()
        mock_loader.load.return_value = {"default": {"extended_key": "extended_value"}}
        mock_loader.source = "test_source"

        # Mock the loader_manager with a proper mock list
        mock_loaders_list = Mock()
        self.config.loader_manager = Mock()
        self.config.loader_manager.loaders = mock_loaders_list

        # Call extend_config (not extend)
        self.extender.extend_config(mock_loader)

        # Verify the loader was added
        mock_loaders_list.append.assert_called_once_with(mock_loader)


if __name__ == "__main__":
    unittest.main()
