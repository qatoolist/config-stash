import logging
import os

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)


class ConfigFileHandler(FileSystemEventHandler):
    """Handles file system events for configuration files."""

    def __init__(self, config):
        self.config = config

    def on_modified(self, event):
        if event.src_path in self.config.get_watched_files():
            logger.info(f"Configuration file {event.src_path} has been modified. Reloading...")
            self.config.reload()


class ConfigFileWatcher:
    def __init__(self, config):
        self.config = config
        self.event_handler = ConfigFileHandler(config)
        self.observer = Observer()

    def start(self):
        for file_path in self.config.get_watched_files():
            directory = os.path.dirname(file_path)
            self.observer.schedule(self.event_handler, path=directory, recursive=False)
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()
