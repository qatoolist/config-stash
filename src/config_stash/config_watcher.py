import logging
import os

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False
    FileSystemEventHandler = object  # type: ignore

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
        if not HAS_WATCHDOG:
            raise ImportError(
                "watchdog is required for dynamic reloading. "
                "Install with: pip install config-stash[watch]"
            )
        self.config = config
        self.event_handler = ConfigFileHandler(config)
        self.observer = Observer()

    def start(self):
        watched_dirs = set()
        for file_path in self.config.get_watched_files():
            directory = os.path.dirname(file_path) or "."
            # Avoid watching the same directory multiple times
            if directory not in watched_dirs:
                self.observer.schedule(self.event_handler, path=directory, recursive=False)
                watched_dirs.add(directory)
        self.observer.start()

    def stop(self):
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
