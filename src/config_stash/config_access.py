"""Configuration access, querying, mutation, and diffing mixin for Config.

Provides methods for reading (get, keys, has), writing (set), querying
(schema, explain, layers), diffing (diff, detect_drift), and change
callbacks (on_change).
"""

import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from config_stash.config_diff import ConfigDiff, ConfigDiffer, ConfigDriftDetector
from config_stash.config_introspection import (
    get_all_keys,
    get_nested_value,
    get_schema_info,
    has_key,
)
from config_stash.exceptions import ConfigNotFoundError

if TYPE_CHECKING:
    from config_stash.config import Config

logger = logging.getLogger(__name__)


class ConfigAccess:
    """Mixin providing read, write, query, diff, and callback capabilities."""

    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary.

        Returns:
            The current configuration as a dictionary
        """
        return self.env_config if self.env_config else self.merged_config

    def keys(self, prefix: str = "") -> List[str]:
        """Get all configuration keys.

        Args:
            prefix: Optional prefix to filter keys

        Returns:
            List of dot-separated key paths

        Example:
            >>> config.keys()
            ['database', 'database.host', 'database.port']
        """
        config_dict = self.to_dict()
        all_keys = get_all_keys(config_dict, "")
        if prefix:
            filtered_keys = [k for k in all_keys if k.startswith(prefix)]
            if prefix and not prefix.endswith("."):
                prefix = prefix + "."
            return [
                k[len(prefix):] if k.startswith(prefix) else k
                for k in filtered_keys
            ]
        return all_keys

    def has(self, key_path: str) -> bool:
        """Check if a configuration key exists.

        Args:
            key_path: Dot-separated key path

        Returns:
            True if key exists
        """
        return has_key(self.to_dict(), key_path)

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get a configuration value by key path with optional default.

        Args:
            key_path: Dot-separated key path
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        config_dict = self.to_dict()
        value = get_nested_value(config_dict, key_path, default)
        if self.hook_processor and value is not None:
            value = self.hook_processor.process_hooks(key_path, value)
        return value

    def schema(self, key_path: str = "") -> Dict[str, Any]:
        """Get schema information for a configuration key or entire config.

        Args:
            key_path: Optional dot-separated key path

        Returns:
            Dictionary with schema information
        """
        config_dict = self.to_dict()
        schema_info = get_schema_info(config_dict, key_path)

        if self._validated_model and hasattr(
            self._validated_model, "model_json_schema"
        ):
            try:
                pydantic_schema = self._validated_model.model_json_schema()
                schema_info["pydantic_schema"] = pydantic_schema
            except Exception:
                pass

        return schema_info

    def explain(self, key_path: str) -> Dict[str, Any]:
        """Explain how a configuration key was resolved.

        Args:
            key_path: Dot-separated key path

        Returns:
            Dictionary with detailed resolution information
        """
        info: Dict[str, Any] = {}

        source_info = self.get_source_info(key_path)
        if source_info:
            info["value"] = source_info.value
            info["source"] = source_info.source_file
            info["loader_type"] = source_info.loader_type
            info["environment"] = source_info.environment
            info["override_count"] = source_info.override_count
        else:
            info["exists"] = False
            info["available_keys"] = self.keys()
            return info

        override_history = self.get_override_history(key_path)
        if override_history:
            info["override_history"] = [
                {
                    "value": h.value,
                    "source": h.source_file,
                    "loader_type": h.loader_type,
                }
                for h in override_history
            ]

        info["schema"] = self.schema(key_path)
        config_dict = self.to_dict()
        info["current_value"] = get_nested_value(config_dict, key_path)

        return info

    @property
    def layers(self) -> List[Dict[str, Any]]:
        """Get the configuration layer stack showing source precedence.

        Returns:
            List of dicts with 'source', 'loader_type', 'keys', 'key_count'.
        """
        result = []
        for config_dict, source in self.configs:
            loader_type = "unknown"
            for loader in self.loader_manager.loaders:
                if getattr(loader, "source", None) == source:
                    loader_type = loader.__class__.__name__
                    break

            flat_keys = get_all_keys(config_dict)
            result.append({
                "source": source,
                "loader_type": loader_type,
                "keys": flat_keys,
                "key_count": len(flat_keys),
            })
        return result

    def diff(self, other: "Config") -> List[ConfigDiff]:
        """Compare this configuration with another.

        Args:
            other: Another Config instance

        Returns:
            List of ConfigDiff objects
        """
        return ConfigDiffer.diff(self.to_dict(), other.to_dict())

    def detect_drift(self, intended_config: "Config") -> List[ConfigDiff]:
        """Detect configuration drift vs intended state.

        Args:
            intended_config: Config representing intended state

        Returns:
            List of ConfigDiff objects representing drift
        """
        detector = ConfigDriftDetector(intended_config.to_dict())
        return detector.detect_drift(self.to_dict())

    def set(self, key_path: str, value: Any, override: bool = True) -> None:
        """Set a configuration value programmatically.

        Args:
            key_path: Dot-separated key path
            value: Value to set
            override: If True, override existing value
        """
        with self._lock:
            self._set_internal(key_path, value, override)

    def _set_internal(self, key_path: str, value: Any, override: bool = True) -> None:
        """Internal set implementation (called under lock)."""
        self._check_frozen()
        config_dict = self.to_dict()
        keys = key_path.split(".")
        current = config_dict

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            elif not isinstance(current[key], dict):
                if override:
                    current[key] = {}
                else:
                    raise ConfigNotFoundError(
                        f"Cannot set '{key_path}': parent '{key}' is not a dictionary",
                        key=key_path,
                    )
            current = current[key]

        final_key = keys[-1]
        if final_key in current and not override:
            raise ConfigNotFoundError(
                f"Key '{key_path}' already exists. Use override=True to replace it.",
                key=key_path,
            )

        current[final_key] = value

        if self.env_config:
            env_current = self.env_config
            for key in keys[:-1]:
                if key not in env_current:
                    env_current[key] = {}
                elif not isinstance(env_current[key], dict):
                    env_current[key] = {}
                env_current = env_current[key]
            env_current[final_key] = value

            from config_stash.utils.dict_utils import set_nested

            set_nested(self.merged_config, key_path, value)
            self._rebuild_state()

        logger.info(f"Set configuration key '{key_path}' = {value}")

        if self.observer:
            self.observer.record_change()
        if self.event_emitter:
            self.event_emitter.emit("set", key_path, value)

    def on_change(self, func: Callable[[str, Any, Any], None]) -> Callable:
        """Decorator to register a callback for configuration changes.

        Args:
            func: Callback function with signature (key, old_value, new_value)

        Returns:
            The decorated function
        """
        self._change_callbacks.append(func)
        return func

    def _trigger_change_callbacks(
        self, old_config: Dict[str, Any], new_config: Dict[str, Any]
    ) -> None:
        """Trigger registered change callbacks for modified values."""
        all_keys = set(old_config.keys()) | set(new_config.keys())

        for key in all_keys:
            old_value = old_config.get(key)
            new_value = new_config.get(key)

            if old_value != new_value:
                for callback in self._change_callbacks:
                    try:
                        callback(key, old_value, new_value)
                    except Exception as e:
                        logger.error(
                            f"Error in change callback for key '{key}': {e}"
                        )
