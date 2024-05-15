import unittest
from unittest.mock import Mock, patch
from config_stash.config_watcher import ConfigFileWatcher

class TestConfigWatcher(unittest.TestCase):
    @patch('config_stash.config_watcher.Observer')
    def setUp(self, mock_observer):
        self.mock_config = Mock()
        self.mock_config.get_watched_files.return_value = ['config.yaml']
        self.watcher = ConfigFileWatcher(self.mock_config)

    def test_start(self):
        self.watcher.start()
        self.watcher.observer.schedule.assert_called_once()

    def test_stop(self):
        self.watcher.start()
        self.watcher.stop()
        self.watcher.observer.stop.assert_called_once()

if __name__ == '__main__':
    unittest.main()