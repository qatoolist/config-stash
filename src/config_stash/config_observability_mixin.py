"""Observability and versioning mixin for Config.

Provides metrics collection, event emission, and configuration versioning
(save, list, rollback) capabilities.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

from config_stash.config_versioning import ConfigVersion, ConfigVersionManager
from config_stash.observability import ConfigEventEmitter, ConfigObserver

logger = logging.getLogger(__name__)


class ConfigObservabilityMixin:
    """Mixin providing observability, events, and versioning for Config."""

    # Declared by Config.__init__ — available via mixin composition
    observer: Optional[ConfigObserver]
    event_emitter: Optional[ConfigEventEmitter]
    version_manager: Optional[ConfigVersionManager]
    env_config: Dict[str, Any]
    merged_config: Dict[str, Any]

    # Methods from other mixins — declared for type-checker visibility
    to_dict: Callable[[], Dict[str, Any]]
    _rebuild_state: Callable[[], None]

    def enable_observability(self) -> ConfigObserver:
        """Enable observability and metrics collection.

        Returns:
            ConfigObserver instance for accessing metrics

        Example:
            >>> observer = config.enable_observability()
            >>> stats = observer.get_statistics()
        """
        self.observer = ConfigObserver()
        return self.observer

    def enable_events(self) -> ConfigEventEmitter:
        """Enable event emission for configuration changes.

        Returns:
            ConfigEventEmitter instance for subscribing to events

        Example:
            >>> emitter = config.enable_events()
            >>> @emitter.on("reload")
            ... def handle_reload(new_config, duration):
            ...     print(f"Config reloaded in {duration}s")
        """
        self.event_emitter = ConfigEventEmitter()
        return self.event_emitter

    def get_metrics(self) -> Optional[Dict[str, Any]]:
        """Get configuration metrics.

        Returns:
            Dictionary with metrics statistics, or None if observability not enabled
        """
        if self.observer:
            return self.observer.get_statistics()
        return None

    def enable_versioning(
        self, storage_path: Optional[str] = None
    ) -> ConfigVersionManager:
        """Enable configuration versioning.

        Args:
            storage_path: Optional path to store version history

        Returns:
            ConfigVersionManager instance
        """
        self.version_manager = ConfigVersionManager(storage_path=storage_path)
        return self.version_manager

    def save_version(
        self, metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[ConfigVersion]:
        """Save current configuration as a version.

        Args:
            metadata: Optional metadata (e.g., author, message)

        Returns:
            ConfigVersion instance if versioning is enabled, None otherwise
        """
        if not self.version_manager:
            self.enable_versioning()

        if self.version_manager:
            return self.version_manager.save_version(self.to_dict(), metadata=metadata)
        return None

    def get_version(self, version_id: str) -> Optional[ConfigVersion]:
        """Get a configuration version by ID.

        Args:
            version_id: Version ID to retrieve

        Returns:
            ConfigVersion instance, or None if not found
        """
        if not self.version_manager:
            return None
        return self.version_manager.get_version(version_id)

    def rollback_to_version(self, version_id: str) -> None:
        """Rollback configuration to a specific version.

        Args:
            version_id: Version ID to rollback to

        Raises:
            ValueError: If version not found or versioning not enabled
        """
        if not self.version_manager:
            raise ValueError("Versioning not enabled. Call enable_versioning() first.")

        config_dict = self.version_manager.rollback(version_id)

        self.env_config = config_dict
        self.merged_config = config_dict
        self._rebuild_state()

        logger.info(f"Configuration rolled back to version: {version_id}")
