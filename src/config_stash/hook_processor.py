from threading import RLock
from typing import Any, Callable, Dict


class HookProcessor:
    """Processes configuration values through registered hooks.

    Thread-safe implementation that can handle concurrent hook registration
    and processing.
    """

    def __init__(self) -> None:
        """Initialize the hook processor with empty hook registries."""
        self.hooks: Dict[str, Any] = {"key": {}, "value": {}, "condition": [], "global": []}
        self._lock = RLock()  # Reentrant lock for thread safety

    def register_key_hook(self, key: str, hook: Callable[[Any], Any]) -> None:
        """Register a hook for a specific configuration key.

        Args:
            key: Configuration key to attach the hook to
            hook: Callable that transforms the configuration value
        """
        with self._lock:
            if key not in self.hooks["key"]:
                self.hooks["key"][key] = []
            self.hooks["key"][key].append(hook)

    def register_value_hook(self, value: Any, hook: Callable[[Any], Any]) -> None:
        """Register a hook for a specific value.

        Args:
            value: Configuration value to attach the hook to
            hook: Callable that transforms the configuration value
        """
        with self._lock:
            if value not in self.hooks["value"]:
                self.hooks["value"][value] = []
            self.hooks["value"][value].append(hook)

    def register_condition_hook(
        self, condition: Callable[[str, Any], bool], hook: Callable[[Any], Any]
    ) -> None:
        """Register a hook that runs when a condition is met.

        Args:
            condition: Callable that returns True when hook should run
            hook: Callable that transforms the configuration value
        """
        with self._lock:
            self.hooks["condition"].append((condition, hook))

    def register_global_hook(self, hook: Callable[[Any], Any]) -> None:
        """Register a hook that runs for all configuration values.

        Args:
            hook: Callable that transforms the configuration value
        """
        with self._lock:
            self.hooks["global"].append(hook)

    def process_hooks(self, key: str, value: Any) -> Any:
        """Process value through all registered hooks.

        Args:
            key: Configuration key being processed
            value: Configuration value to process

        Returns:
            Transformed value after applying all applicable hooks
        """
        # Create thread-safe copies of hooks to avoid iteration issues
        with self._lock:
            key_hooks = self.hooks["key"].get(key, [])[:]
            # Only use value as key if it's hashable (avoid dict/list issues)
            if isinstance(value, (dict, list)):
                value_hooks = []
            else:
                value_hooks = self.hooks["value"].get(value, [])[:]
            condition_hooks = self.hooks["condition"][:]
            global_hooks = self.hooks["global"][:]

        # Process hooks outside the lock to avoid deadlocks
        for hook in key_hooks:
            value = hook(value)

        for hook in value_hooks:
            value = hook(value)

        for condition, hook in condition_hooks:
            if condition(key, value):
                value = hook(value)

        for hook in global_hooks:
            value = hook(value)

        return value
