"""File change tracking for incremental configuration reloading.

This module provides utilities for tracking file modifications to enable
incremental reloading of only changed configuration sources.
"""

import hashlib
import logging
import os
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class FileTracker:
    """Tracks file modification times and hashes for change detection.

    This class provides efficient change detection for configuration files
    by tracking file modification times and SHA256 hashes. It enables
    incremental reloading by identifying which files have changed.

    Attributes:
        _file_hashes: Dictionary mapping file paths to their SHA256 hashes
        _file_mtimes: Dictionary mapping file paths to modification timestamps

    Example:
        >>> tracker = FileTracker()
        >>> tracker.track_file("config.yaml")
        >>> if tracker.has_changed("config.yaml"):
        ...     print("File changed, reload needed")
        ...     tracker.update_tracking("config.yaml")
    """

    def __init__(self) -> None:
        """Initialize the file tracker.

        Creates a new FileTracker instance with empty tracking dictionaries.
        Files must be explicitly tracked using track_file() or update_tracking().
        """
        self._file_hashes: Dict[str, str] = {}
        self._file_mtimes: Dict[str, float] = {}

    def get_file_hash(self, file_path: str) -> Optional[str]:
        """Calculate SHA256 hash of a file.

        Args:
            file_path: Path to the file

        Returns:
            SHA256 hash as hex string, or None if file doesn't exist
        """
        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, "rb") as f:
                file_hash = hashlib.sha256()
                while chunk := f.read(8192):
                    file_hash.update(chunk)
                return file_hash.hexdigest()
        except Exception as e:
            logger.warning(f"Failed to calculate hash for {file_path}: {e}")
            return None

    def get_file_mtime(self, file_path: str) -> Optional[float]:
        """Get file modification time.

        Args:
            file_path: Path to the file

        Returns:
            Modification time as float, or None if file doesn't exist
        """
        if not os.path.exists(file_path):
            return None

        try:
            return os.path.getmtime(file_path)
        except Exception as e:
            logger.warning(f"Failed to get mtime for {file_path}: {e}")
            return None

    def track_file(self, file_path: str) -> None:
        """Track a file for change detection.

        Args:
            file_path: Path to the file to track
        """
        if not os.path.exists(file_path):
            return

        self._file_hashes[file_path] = self.get_file_hash(file_path) or ""
        self._file_mtimes[file_path] = self.get_file_mtime(file_path) or 0.0

    def has_changed(self, file_path: str) -> bool:
        """Check if a tracked file has changed.

        Args:
            file_path: Path to the file to check

        Returns:
            True if file has changed or is not tracked, False otherwise
        """
        if file_path not in self._file_hashes:
            # File not tracked yet - consider it as changed
            return True

        if not os.path.exists(file_path):
            # File was deleted
            return True

        # Check modification time first (faster)
        current_mtime = self.get_file_mtime(file_path)
        if current_mtime is None:
            return True

        if current_mtime != self._file_mtimes.get(file_path):
            return True

        # Check hash for definitive change detection
        current_hash = self.get_file_hash(file_path)
        if current_hash is None:
            return True

        return current_hash != self._file_hashes.get(file_path)

    def update_tracking(self, file_path: str) -> None:
        """Update tracking information for a file.

        Args:
            file_path: Path to the file to update
        """
        self.track_file(file_path)

    def get_changed_files(self, file_paths: list) -> list:
        """Get list of files that have changed.

        Args:
            file_paths: List of file paths to check

        Returns:
            List of file paths that have changed
        """
        changed = []
        for file_path in file_paths:
            if self.has_changed(file_path):
                changed.append(file_path)
        return changed

    def clear(self) -> None:
        """Clear all tracking information."""
        self._file_hashes.clear()
        self._file_mtimes.clear()
