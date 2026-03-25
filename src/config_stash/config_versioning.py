"""Configuration versioning and history management for Config-Stash.

This module provides versioning capabilities for configurations, allowing
tracking of changes over time and rollback functionality.
"""

import copy
import hashlib
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ConfigVersion:
    """Represents a version of a configuration."""

    def __init__(
        self,
        version_id: str,
        config_dict: Dict[str, Any],
        timestamp: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize a configuration version.

        Args:
            version_id: Unique version identifier
            config_dict: Configuration dictionary for this version
            timestamp: Version timestamp (default: current time)
            metadata: Optional metadata dictionary
        """
        self.version_id = version_id
        self.config_dict = config_dict
        self.timestamp = timestamp or time.time()
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert version to dictionary.

        Returns:
            Dictionary representation of the version
        """
        return {
            "version_id": self.version_id,
            "config": self.config_dict,
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConfigVersion":
        """Create ConfigVersion from dictionary.

        Args:
            data: Dictionary containing version data

        Returns:
            ConfigVersion instance
        """
        return cls(
            version_id=data["version_id"],
            config_dict=data["config"],
            timestamp=data.get("timestamp"),
            metadata=data.get("metadata", {}),
        )


class ConfigVersionManager:
    """Manages configuration versions and history."""

    DEFAULT_MAX_VERSIONS = 100

    def __init__(
        self,
        storage_path: Optional[str] = None,
        max_versions: Optional[int] = None,
    ) -> None:
        """Initialize version manager.

        Args:
            storage_path: Path to store version history (default: .config_stash/versions)
            max_versions: Maximum number of versions to keep. Oldest versions
                are evicted when the limit is reached. None means use default (100).
        """
        if storage_path is None:
            storage_path = ".config_stash/versions"
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.max_versions = max_versions or self.DEFAULT_MAX_VERSIONS
        self._versions: Dict[str, ConfigVersion] = {}

    def _generate_version_id(self, config_dict: Dict[str, Any]) -> str:
        """Generate a unique version ID from configuration content and timestamp.

        Args:
            config_dict: Configuration dictionary

        Returns:
            Version ID (SHA256 hash prefix)
        """
        config_str = json.dumps(config_dict, sort_keys=True)
        # Include timestamp to ensure unique IDs even for identical content
        unique_str = f"{config_str}:{time.time()}"
        config_hash = hashlib.sha256(unique_str.encode()).hexdigest()
        return config_hash[:16]  # Use first 16 chars

    def save_version(
        self,
        config_dict: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ConfigVersion:
        """Save a new configuration version.

        Args:
            config_dict: Configuration dictionary to version
            metadata: Optional metadata (e.g., author, message)

        Returns:
            ConfigVersion instance

        Example:
            >>> manager = ConfigVersionManager()
            >>> version = manager.save_version(
            ...     config_dict,
            ...     metadata={"author": "user@example.com", "message": "Updated database config"}
            ... )
        """
        version_id = self._generate_version_id(config_dict)
        # Create a deep copy to avoid reference mutations
        version = ConfigVersion(
            version_id=version_id, config_dict=copy.deepcopy(config_dict), metadata=metadata
        )
        self._versions[version_id] = version

        # Persist to disk
        version_file = self.storage_path / f"{version_id}.json"
        with open(version_file, "w") as f:
            json.dump(version.to_dict(), f, indent=2)

        # Evict oldest versions if over limit
        if len(self._versions) > self.max_versions:
            sorted_versions = sorted(
                self._versions.values(), key=lambda v: v.timestamp
            )
            for old_version in sorted_versions[: len(self._versions) - self.max_versions]:
                old_file = self.storage_path / f"{old_version.version_id}.json"
                if old_file.exists():
                    old_file.unlink()
                del self._versions[old_version.version_id]

        logger.info(f"Saved configuration version: {version_id}")
        return version

    def get_version(self, version_id: str) -> Optional[ConfigVersion]:
        """Get a configuration version by ID.

        Args:
            version_id: Version ID to retrieve

        Returns:
            ConfigVersion instance, or None if not found

        Example:
            >>> version = manager.get_version("abc123")
            >>> if version:
            ...     config = version.config_dict
        """
        # Check cache first
        if version_id in self._versions:
            return self._versions[version_id]

        # Load from disk
        version_file = self.storage_path / f"{version_id}.json"
        if version_file.exists():
            try:
                with open(version_file, "r") as f:
                    data = json.load(f)
                version = ConfigVersion.from_dict(data)
                self._versions[version_id] = version
                return version
            except Exception as e:
                logger.warning(f"Failed to load version {version_id}: {e}")

        return None

    def list_versions(self, limit: Optional[int] = None) -> List[ConfigVersion]:
        """List all configuration versions.

        Args:
            limit: Optional limit on number of versions to return

        Returns:
            List of ConfigVersion instances, sorted by timestamp (newest first)

        Example:
            >>> versions = manager.list_versions(limit=10)
            >>> for version in versions:
            ...     print(f"{version.version_id}: {version.timestamp}")
        """
        versions: List[ConfigVersion] = []

        # Always scan disk to pick up versions from other processes
        for version_file in self.storage_path.glob("*.json"):
            try:
                version_id = version_file.stem
                if version_id not in self._versions:
                    with open(version_file, "r") as f:
                        data = json.load(f)
                    version = ConfigVersion.from_dict(data)
                    self._versions[version.version_id] = version
            except Exception as e:
                logger.warning(f"Failed to load version file {version_file}: {e}")

        versions = sorted(self._versions.values(), key=lambda v: v.timestamp, reverse=True)

        if limit:
            versions = versions[:limit]

        return versions

    def get_latest_version(self) -> Optional[ConfigVersion]:
        """Get the latest configuration version.

        Returns:
            Latest ConfigVersion instance, or None if no versions exist
        """
        versions = self.list_versions(limit=1)
        return versions[0] if versions else None

    def rollback(self, version_id: str) -> Dict[str, Any]:
        """Rollback to a specific configuration version.

        Args:
            version_id: Version ID to rollback to

        Returns:
            Configuration dictionary from the specified version

        Raises:
            ValueError: If version not found

        Example:
            >>> config_dict = manager.rollback("abc123")
            >>> # Use config_dict to restore configuration
        """
        version = self.get_version(version_id)
        if not version:
            raise ValueError(f"Version {version_id} not found")

        logger.info(f"Rolling back to version: {version_id}")
        return copy.deepcopy(version.config_dict)

    def diff_versions(self, version_id1: str, version_id2: str) -> List[Any]:
        """Compare two configuration versions.

        Args:
            version_id1: First version ID
            version_id2: Second version ID

        Returns:
            List of differences between versions

        Example:
            >>> diffs = manager.diff_versions("abc123", "def456")
            >>> for diff in diffs:
            ...     print(f"{diff.key}: {diff.diff_type.value}")
        """
        from config_stash.config_diff import ConfigDiffer

        version1 = self.get_version(version_id1)
        version2 = self.get_version(version_id2)

        if not version1 or not version2:
            raise ValueError("One or both versions not found")

        return ConfigDiffer.diff(version1.config_dict, version2.config_dict)
