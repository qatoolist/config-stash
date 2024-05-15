import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ConfigFileHandler(FileSystemEventHandler):
    def __init__(self, config):
        self.config = config

    def on_modified(self, event):
        if event.src_path in self.config.get_watched_files():
            print(f"Configuration file {event.src_path} has been modified. Reloading...")
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