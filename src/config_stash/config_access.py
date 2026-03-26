"""Configuration access, querying, mutation, and diffing mixin for Config.

Provides methods for reading (get, keys, has), writing (set), querying
(schema, explain, layers), diffing (diff, detect_drift), and change
callbacks (on_change).
"""

from __future__ import annotations

import copy
import logging
import threading
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterator, List, Optional

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
    from config_stash.hook_processor import HookProcessor
    from config_stash.loader_manager import LoaderManager
    from config_stash.observability import ConfigEventEmitter, ConfigObserver

logger = logging.getLogger(__name__)


class ConfigAccess:
    """Mixin providing read, write, query, diff, and callback capabilities."""

    # Declared by Config.__init__ — available via mixin composition
    env_config: Dict[str, Any]
    merged_config: Dict[str, Any]
    hook_processor: HookProcessor
    _validated_model: Optional[Any]
    _lock: threading.RLock
    _frozen: bool
    observer: Optional[ConfigObserver]
    event_emitter: Optional[ConfigEventEmitter]
    configs: List[Any]
    loader_manager: LoaderManager
    _change_callbacks: List[Callable[..., Any]]
    _sysenv_fallback: bool
    _env_prefix: Optional[str]

    # Methods from other mixins — declared for type-checker visibility
    _check_frozen: Callable[[], None]
    _sysenv_lookup: Callable[..., Any]
    _rebuild_state: Callable[[], None]
    get_source_info: Callable[..., Any]
    get_override_history: Callable[..., Any]

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
                k[len(prefix) :] if k.startswith(prefix) else k for k in filtered_keys
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

        If ``sysenv_fallback=True`` was set at init and the key is not found
        in file-based config, the corresponding environment variable is checked
        automatically (e.g., ``database.host`` → ``DATABASE_HOST``).

        Args:
            key_path: Dot-separated key path
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        _sentinel = object()
        config_dict = self.to_dict()
        value = get_nested_value(config_dict, key_path, _sentinel)

        # sysenv_fallback: check env vars when key not in file config
        if value is _sentinel and self._sysenv_fallback:
            env_value = self._sysenv_lookup(key_path)
            if env_value is not None:
                from config_stash.utils.type_coercion import parse_scalar_value

                value = parse_scalar_value(env_value)

        if value is _sentinel:
            value = default

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
            result.append(
                {
                    "source": source,
                    "loader_type": loader_type,
                    "keys": flat_keys,
                    "key_count": len(flat_keys),
                }
            )
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

    @contextmanager
    def override(self, overrides: Dict[str, Any]) -> Iterator[None]:
        """Context manager that temporarily overrides configuration values.

        On entry, the current ``env_config`` and ``merged_config`` are saved
        (deep-copied) and the *overrides* are applied.  On exit the original
        state is restored, even if the body raised an exception.

        Works with frozen configs (temporarily unfreezes, re-freezes on exit).
        Supports nesting — each level saves/restores independently.

        Args:
            overrides: Mapping of dot-separated key paths to override values.

        Example:
            >>> with config.override({"database.host": "test-db"}):
            ...     assert config.get("database.host") == "test-db"
        """
        from config_stash.utils.dict_utils import set_nested

        with self._lock:
            # Snapshot current state
            saved_env_config = copy.deepcopy(self.env_config)
            saved_merged_config = copy.deepcopy(self.merged_config)
            was_frozen = self._frozen

            # Temporarily unfreeze so we can apply overrides
            if was_frozen:
                self._frozen = False

            # Apply overrides
            for key_path, value in overrides.items():
                set_nested(self.env_config, key_path, value)
                set_nested(self.merged_config, key_path, value)
            self._rebuild_state()

            # Re-freeze if it was frozen (reads still work while frozen)
            if was_frozen:
                self._frozen = True

        try:
            yield
        finally:
            with self._lock:
                # Restore original state
                was_frozen_now = self._frozen
                if was_frozen_now:
                    self._frozen = False
                self.env_config = saved_env_config
                self.merged_config = saved_merged_config
                self._rebuild_state()
                if was_frozen:
                    self._frozen = True

    def generate_docs(self, format: str = "markdown") -> str:
        """Generate documentation for all configuration keys.

        Iterates all keys and produces a reference document with key names,
        types, current values, and sources.  When a Pydantic schema has been
        validated (``_validated_model`` is set and its *class* exposes
        ``model_fields``), the output also includes field descriptions,
        default values, and required/optional status.

        Args:
            format: Output format — ``"markdown"`` or ``"json"``.

        Returns:
            Formatted documentation string.

        Raises:
            ValueError: If *format* is not ``"markdown"`` or ``"json"``.

        Example:
            >>> docs = config.generate_docs()
            >>> print(docs)
        """
        import json as _json

        if format not in ("markdown", "json"):
            raise ValueError(
                f"Unsupported docs format '{format}'. Use 'markdown' or 'json'."
            )

        config_dict = self.to_dict()
        all_keys = get_all_keys(config_dict, "")

        # Build Pydantic field metadata lookup (field_name -> info dict)
        pydantic_fields: Dict[str, Dict[str, Any]] = {}
        schema_class = getattr(self, "_schema", None)
        if schema_class is not None:
            try:
                from pydantic import BaseModel

                if isinstance(schema_class, type) and issubclass(
                    schema_class, BaseModel
                ):
                    for field_name, field_info in schema_class.model_fields.items():
                        pydantic_fields[field_name] = {
                            "description": field_info.description or "",
                            "default": (
                                repr(field_info.default)
                                if field_info.default is not None
                                else ""
                            ),
                            "required": field_info.is_required(),
                            "annotation": (
                                getattr(field_info.annotation, "__name__", "")
                                if field_info.annotation is not None
                                else ""
                            ),
                        }
            except ImportError:
                pass

        # Only keep leaf keys (keys whose values are not dicts)
        leaf_keys = [
            k for k in all_keys
            if not isinstance(get_nested_value(config_dict, k), dict)
        ]

        rows: List[Dict[str, Any]] = []
        for key in sorted(leaf_keys):
            value = get_nested_value(config_dict, key)
            value_type = type(value).__name__

            # Source info
            source_info = self.get_source_info(key)
            source = source_info.source_file if source_info else ""

            row: Dict[str, Any] = {
                "key": key,
                "type": value_type,
                "current_value": value,
                "source": source,
            }

            # Enrich with Pydantic metadata if available
            pydantic_key = key.replace(".", "_")
            if pydantic_key in pydantic_fields:
                pf = pydantic_fields[pydantic_key]
                row["description"] = pf["description"]
                row["default"] = pf["default"]
                row["required"] = pf["required"]
                if pf["annotation"]:
                    row["type"] = pf["annotation"]

            rows.append(row)

        if format == "json":
            return _json.dumps(rows, indent=2, default=str)

        # --- Markdown format ---
        has_pydantic = bool(pydantic_fields)

        lines: List[str] = [
            "# Configuration Reference",
            "",
            "Generated from loaded configuration.",
            "",
            "## Keys",
            "",
        ]

        if has_pydantic:
            lines.append(
                "| Key | Type | Current Value | Source "
                "| Description | Default | Required |"
            )
            lines.append(
                "|-----|------|---------------|--------"
                "|-------------|---------|----------|"
            )
        else:
            lines.append(
                "| Key | Type | Current Value | Source |"
            )
            lines.append(
                "|-----|------|---------------|--------|"
            )

        for row in rows:
            val_str = str(row["current_value"])
            if has_pydantic:
                desc = row.get("description", "")
                default = row.get("default", "")
                required = row.get("required", "")
                if isinstance(required, bool):
                    required = "Yes" if required else "No"
                lines.append(
                    f"| `{row['key']}` | {row['type']} | {val_str} "
                    f"| {row['source']} | {desc} | {default} | {required} |"
                )
            else:
                lines.append(
                    f"| `{row['key']}` | {row['type']} | {val_str} "
                    f"| {row['source']} |"
                )

        lines.append("")
        return "\n".join(lines)

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
                        logger.error(f"Error in change callback for key '{key}': {e}")
