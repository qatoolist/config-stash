# pyright: reportAttributeAccessIssue=false
from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from config_stash.config import Config

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False
    FileSystemEventHandler = object  # type: ignore[reportAssignmentType]
    Observer = object  # type: ignore[reportAssignmentType]

logger = logging.getLogger(__name__)


class ConfigFileHandler(FileSystemEventHandler):  # type: ignore[reportGeneralTypeIssues]
    """Handles file system events for configuration files.

    ConfigFileHandler listens for file modification events from the
    watchdog library and triggers a configuration reload when a watched
    configuration file is modified. It acts as the bridge between the
    OS-level file system notifications and the Config reload mechanism.

    Attributes:
        config: The Config instance whose files are being watched.
            Must implement ``get_watched_files()`` and ``reload()`` methods.

    Example:
        >>> from config_stash.config_watcher import ConfigFileHandler
        >>> handler = ConfigFileHandler(config)
        >>> # The handler is typically used internally by ConfigFileWatcher,
        >>> # but can be passed to a watchdog Observer directly:
        >>> from watchdog.observers import Observer
        >>> observer = Observer()
        >>> observer.schedule(handler, path="/etc/myapp", recursive=False)
    """

    def __init__(self, config: Config) -> None:
        """Initialize the file system event handler.

        Args:
            config: A Config instance that provides ``get_watched_files()``
                (returning a set of absolute file paths) and ``reload()``
                methods.
        """
        self.config = config

    def on_modified(self, event: Any) -> None:
        """Handle a file modification event.

        Called by the watchdog observer whenever a file in a watched
        directory is modified. If the modified file is one of the
        configuration files being tracked, the configuration is reloaded.

        Args:
            event: A watchdog ``FileModifiedEvent`` containing ``src_path``,
                the absolute path of the modified file.
        """
        if event.src_path in self.config.get_watched_files():
            logger.info(f"Configuration file {event.src_path} has been modified. Reloading...")
            self.config.reload()


class ConfigFileWatcher:
    """Watches configuration files for changes and triggers automatic reloads.

    ConfigFileWatcher uses the ``watchdog`` library to monitor the file system
    for modifications to configuration files. When a watched file changes,
    the associated Config instance is automatically reloaded, enabling live
    configuration updates without application restarts.

    The watcher identifies which directories contain watched files and sets
    up a single observer per directory to avoid duplicate event handling.

    Attributes:
        config: The Config instance whose files are being watched.
        event_handler: The ConfigFileHandler that processes file events.
        observer: The watchdog Observer thread that monitors directories.

    Example:
        >>> from config_stash import Config
        >>> from config_stash.config_watcher import ConfigFileWatcher
        >>>
        >>> config = Config(loaders=[YamlLoader("app.yaml")])
        >>> watcher = ConfigFileWatcher(config)
        >>> watcher.start()
        >>> # Config will now auto-reload when app.yaml changes
        >>> # ...
        >>> watcher.stop()

    Note:
        Requires the ``watchdog`` package. Install it with::

            pip install config-stash[watch]
    """

    def __init__(self, config: Config) -> None:
        """Initialize the configuration file watcher.

        Args:
            config: A Config instance that provides ``get_watched_files()``
                and ``reload()`` methods.

        Raises:
            ImportError: If the ``watchdog`` package is not installed.
        """
        if not HAS_WATCHDOG:
            raise ImportError(
                "watchdog is required for dynamic reloading. "
                "Install with: pip install config-stash[watch]"
            )
        self.config = config
        self.event_handler = ConfigFileHandler(config)
        self.observer = Observer()  # type: ignore[reportPossiblyUnboundVariable]

    def start(self) -> None:
        """Start watching configuration files for changes.

        Identifies all unique directories containing watched configuration
        files and schedules a watchdog observer for each directory. The
        observer runs in a background daemon thread.

        Raises:
            OSError: If a watched directory does not exist or is not readable.

        Example:
            >>> watcher = ConfigFileWatcher(config)
            >>> watcher.start()
            >>> # Files are now being monitored
        """
        watched_dirs = set()
        for file_path in self.config.get_watched_files():
            directory = os.path.dirname(file_path) or "."
            # Avoid watching the same directory multiple times
            if directory not in watched_dirs:
                self.observer.schedule(self.event_handler, path=directory, recursive=False)
                watched_dirs.add(directory)
        self.observer.start()

    def stop(self) -> None:
        """Stop watching configuration files.

        Gracefully shuts down the watchdog observer thread. If the observer
        is not running, this method is a no-op.

        Example:
            >>> watcher.stop()
        """
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
