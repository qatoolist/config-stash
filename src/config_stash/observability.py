"""Observability and metrics for Config-Stash.

This module provides metrics collection and observability features
for monitoring configuration usage, access patterns, and performance.
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ConfigAccessMetric:
    """Represents a configuration access metric.

    This dataclass tracks metrics for a single configuration key, including
    access frequency and timing information.

    Attributes:
        key: The configuration key being tracked
        access_count: Total number of times this key has been accessed
        first_access: Timestamp of the first access (seconds since epoch)
        last_access: Timestamp of the most recent access (seconds since epoch)
        avg_access_time: Average time taken to access this key (in seconds)
        total_access_time: Total time spent accessing this key (in seconds)
    """

    key: str
    access_count: int = 0
    first_access: Optional[float] = None
    last_access: Optional[float] = None
    avg_access_time: float = 0.0
    total_access_time: float = 0.0

    def record_access(self, access_time: float = 0.0) -> None:
        """Record an access to this configuration key.

        Args:
            access_time: Time taken to access the key (in seconds)
        """
        current_time = time.time()
        self.access_count += 1
        self.total_access_time += access_time
        self.avg_access_time = self.total_access_time / self.access_count

        if self.first_access is None:
            self.first_access = current_time
        self.last_access = current_time


@dataclass
class ConfigMetrics:
    """Configuration metrics and statistics.

    This dataclass aggregates metrics for configuration usage, including
    access patterns, reload frequency, and change tracking.

    Attributes:
        total_keys: Total number of keys in the configuration
        accessed_keys: Number of unique keys that have been accessed
        reload_count: Total number of times configuration has been reloaded
        last_reload: Timestamp of the last reload (seconds since epoch)
        reload_durations: List of reload durations (in seconds) for performance tracking
        access_metrics: Dictionary mapping key paths to ConfigAccessMetric instances
        change_count: Total number of configuration changes recorded
        last_change: Timestamp of the last configuration change (seconds since epoch)
    """

    total_keys: int = 0
    accessed_keys: int = 0
    reload_count: int = 0
    last_reload: Optional[float] = None
    reload_durations: List[float] = field(default_factory=list)
    access_metrics: Dict[str, ConfigAccessMetric] = field(default_factory=dict)
    change_count: int = 0
    last_change: Optional[float] = None

    MAX_RELOAD_DURATIONS = 1000  # Cap stored durations to prevent unbounded growth

    def record_reload(self, duration: float) -> None:
        """Record a configuration reload.

        Args:
            duration: Reload duration in seconds
        """
        self.reload_count += 1
        self.last_reload = time.time()
        self.reload_durations.append(duration)
        # Evict oldest entries to prevent unbounded memory growth
        if len(self.reload_durations) > self.MAX_RELOAD_DURATIONS:
            self.reload_durations = self.reload_durations[-self.MAX_RELOAD_DURATIONS:]

    def record_change(self) -> None:
        """Record a configuration change."""
        self.change_count += 1
        self.last_change = time.time()

    def record_access(self, key: str, access_time: float = 0.0) -> None:
        """Record a configuration key access.

        Args:
            key: Configuration key accessed
            access_time: Time taken to access (in seconds)
        """
        if key not in self.access_metrics:
            self.access_metrics[key] = ConfigAccessMetric(key=key)
        self.access_metrics[key].record_access(access_time)

    def get_statistics(self) -> Dict[str, Any]:
        """Get metrics statistics.

        Returns:
            Dictionary with metrics statistics
        """
        avg_reload_time = (
            sum(self.reload_durations) / len(self.reload_durations)
            if self.reload_durations
            else 0.0
        )

        top_accessed = sorted(
            self.access_metrics.values(),
            key=lambda m: m.access_count,
            reverse=True,
        )[:10]

        return {
            "total_keys": self.total_keys,
            "accessed_keys": len(self.access_metrics),
            "access_rate": (
                len(self.access_metrics) / self.total_keys if self.total_keys > 0 else 0.0
            ),
            "reload_count": self.reload_count,
            "last_reload": self.last_reload,
            "avg_reload_time": avg_reload_time,
            "change_count": self.change_count,
            "last_change": self.last_change,
            "top_accessed_keys": [
                {
                    "key": m.key,
                    "count": m.access_count,
                    "avg_time": m.avg_access_time,
                }
                for m in top_accessed
            ],
        }


class ConfigObserver:
    """Observer for configuration access and changes.

    This class tracks configuration usage patterns, access frequencies,
    and performance metrics for observability purposes. It can be enabled
    on a Config instance to automatically collect metrics during normal usage.

    Attributes:
        metrics: ConfigMetrics instance containing collected metrics
        _enabled: Whether metrics collection is currently enabled

    Example:
        >>> from config_stash import Config
        >>> config = Config(loaders=[YamlLoader("config.yaml")])
        >>> observer = config.enable_observability()
        >>> # Use config normally - metrics are collected automatically
        >>> host = config.database.host
        >>> metrics = observer.get_statistics()
        >>> print(f"Config accessed {metrics['accessed_keys']} times")
    """

    def __init__(self) -> None:
        """Initialize the config observer.

        Creates a new observer instance with metrics collection enabled by default.
        """
        self.metrics = ConfigMetrics()
        self._enabled = True

    def enable(self) -> None:
        """Enable metrics collection.

        When enabled, the observer will track all configuration access,
        reloads, and changes.
        """
        self._enabled = True

    def disable(self) -> None:
        """Disable metrics collection.

        When disabled, the observer stops tracking metrics but retains
        previously collected data.
        """
        self._enabled = False

    def record_key_access(self, key: str, access_time: float = 0.0) -> None:
        """Record a configuration key access.

        Args:
            key: Configuration key accessed
            access_time: Time taken to access (in seconds)
        """
        if self._enabled:
            self.metrics.record_access(key, access_time)

    def record_reload(self, duration: float) -> None:
        """Record a configuration reload.

        Args:
            duration: Reload duration in seconds
        """
        if self._enabled:
            self.metrics.record_reload(duration)

    def record_change(self) -> None:
        """Record a configuration change."""
        if self._enabled:
            self.metrics.record_change()

    def get_metrics(self) -> ConfigMetrics:
        """Get current metrics.

        Returns:
            ConfigMetrics instance
        """
        return self.metrics

    def get_statistics(self) -> Dict[str, Any]:
        """Get metrics statistics.

        Returns a dictionary containing aggregated statistics about configuration
        usage, including access patterns, reload performance, and top accessed keys.

        Returns:
            Dictionary with metrics statistics including:
                - total_keys: Total number of configuration keys
                - accessed_keys: Number of unique keys accessed
                - access_rate: Ratio of accessed keys to total keys
                - reload_count: Number of times config was reloaded
                - avg_reload_time: Average reload duration in seconds
                - change_count: Number of configuration changes
                - top_accessed_keys: List of most frequently accessed keys

        Example:
            >>> stats = observer.get_statistics()
            >>> print(f"Top accessed key: {stats['top_accessed_keys'][0]['key']}")
            >>> print(f"Average reload time: {stats['avg_reload_time']:.3f}s")
        """
        return self.metrics.get_statistics()

    def reset_metrics(self) -> None:
        """Reset all metrics to initial state.

        Clears all collected metrics, including access history, reload durations,
        and change tracking. Useful for starting fresh metrics collection.

        Example:
            >>> observer.reset_metrics()
            >>> # Metrics are now reset to zero
        """
        self.metrics = ConfigMetrics()


class ConfigEventEmitter:
    """Event emitter for configuration events.

    This class provides a simple event emitter pattern for configuration
    events, allowing listeners to subscribe to configuration changes,
    reloads, and other events. Supports multiple listeners per event type.

    Attributes:
        _listeners: Dictionary mapping event names to lists of callback functions

    Example:
        >>> from config_stash import Config
        >>> config = Config(loaders=[YamlLoader("config.yaml")])
        >>> emitter = config.enable_events()
        >>>
        >>> @emitter.on("reload")
        ... def handle_reload(new_config, duration):
        ...     print(f"Config reloaded in {duration:.3f}s")
        >>>
        >>> @emitter.on("change")
        ... def handle_change(old_config, new_config):
        ...     print("Configuration changed")
    """

    def __init__(self) -> None:
        """Initialize the event emitter.

        Creates a new event emitter with an empty listener registry.
        """
        self._listeners: Dict[str, List[Callable]] = defaultdict(list)

    def on(self, event: str, callback: Optional[Callable] = None) -> Callable:
        """Register an event listener.

        Can be used as a decorator or called directly:

            # As decorator
            @emitter.on("reload")
            def handle_reload():
                print("Configuration reloaded")

            # Direct call
            emitter.on("reload", handle_reload)

        Args:
            event: Event name (e.g., "reload", "change", "access")
            callback: Callback function. If None, returns a decorator.

        Returns:
            The callback function (for decorator chaining)
        """
        if callback is not None:
            self._listeners[event].append(callback)
            return callback

        # Decorator mode: emitter.on("event") returns a decorator
        def decorator(fn: Callable) -> Callable:
            self._listeners[event].append(fn)
            return fn

        return decorator

    def off(self, event: str, callback: Callable) -> None:
        """Unregister an event listener.

        Args:
            event: Event name
            callback: Callback function to remove
        """
        if callback in self._listeners[event]:
            self._listeners[event].remove(callback)

    def emit(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Emit an event to all listeners.

        Args:
            event: Event name
            *args: Positional arguments for listeners
            **kwargs: Keyword arguments for listeners

        Example:
            >>> emitter.emit("reload", config_dict)
        """
        for callback in self._listeners[event]:
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in event listener for {event}: {e}")
