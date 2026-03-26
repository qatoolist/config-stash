# pyright: reportIncompatibleMethodOverride=false
"""Main Config class — assembles all mixin capabilities.

This module defines the ``Config`` class which inherits from focused mixin
classes to keep the codebase modular while presenting a single public API.

Mixins:
    - ConfigLoading: load, reload, merge, file watch, hooks
    - ConfigAccess: get, set, keys, has, schema, explain, diff, layers
    - ConfigDebug: source tracking, debug reports, conflict detection
    - ConfigObservabilityMixin: metrics, events, versioning
    - ConfigValidation: Pydantic and JSON Schema validation
"""

import logging
import os
import threading
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Sequence,
    Type,
    TypeVar,
    overload,
)

T = TypeVar("T")

if TYPE_CHECKING:
    from config_stash.config_builder import ConfigBuilder
    from config_stash.loaders.loader import Loader

from config_stash.attribute_accessor import AttributeAccessor
from config_stash.config_access import ConfigAccess
from config_stash.config_composition import ConfigComposer
from config_stash.config_debug import ConfigDebug
from config_stash.config_extender import ConfigExtender
from config_stash.config_loader import ConfigLoader
from config_stash.config_loading import ConfigLoading
from config_stash.config_observability_mixin import ConfigObservabilityMixin
from config_stash.config_reader import get_default_loaders, get_default_settings
from config_stash.config_validation_mixin import ConfigValidation
from config_stash.config_versioning import ConfigVersionManager
from config_stash.config_watcher import ConfigFileWatcher
from config_stash.enhanced_source_tracker import EnhancedSourceTracker
from config_stash.environment_handler import EnvironmentHandler
from config_stash.file_tracker import FileTracker
from config_stash.hook_processor import HookProcessor
from config_stash.hooks.env_var_expander import EnvVarExpander
from config_stash.hooks.type_casting import TypeCasting
from config_stash.loader_manager import LoaderManager
from config_stash.observability import ConfigEventEmitter, ConfigObserver
from config_stash.utils.lazy_loader import LazyLoader

logger = logging.getLogger(__name__)


class Config(
    Generic[T],
    ConfigLoading,
    ConfigAccess,
    ConfigDebug,
    ConfigObservabilityMixin,
    ConfigValidation,
):
    """Main configuration management class for Config-Stash.

    Supports generic typing for full IDE autocomplete and mypy support
    when used with a Pydantic model schema:

        config = Config[AppConfig](
            loaders=[YamlLoader("config.yaml")],
            schema=AppConfig,
            validate_on_load=True,
        )
        config.typed.database.host   # IDE knows this is str
        config.typed.database.port   # IDE knows this is int

    Without a type parameter, Config works as an untyped config object
    with dynamic attribute access (backward compatible):

        config = Config(loaders=[YamlLoader("config.yaml")])
        config.database.host   # type: Any

    Thread Safety:
        - ``reload()`` and ``set()`` are protected by an ``RLock``, ensuring
          that concurrent mutations do not corrupt internal state.
        - ``__getattr__`` (read access) is safe to call concurrently from
          multiple threads without external synchronisation.
        - ``freeze()`` makes the config fully thread-safe by preventing all
          further writes.
        - File watcher callbacks run in a separate thread and are
          lock-protected, so reloads triggered by file changes are serialised.
        - ``HookProcessor`` uses its own ``RLock`` for thread-safe hook
          registration and execution.

    Versioning:
        This library follows Semantic Versioning. Pre-1.0 releases may include
        breaking changes in minor versions. Post-1.0, breaking changes will
        only occur in major versions with deprecation warnings in the prior
        minor release.

    Attributes:
        env: Current environment name
        dynamic_reloading: Whether file watching is enabled
        merged_config: The complete merged configuration dictionary
        env_config: Environment-specific configuration
    """

    def __init__(
        self,
        env: Optional[str] = None,
        loaders: Optional[Sequence["Loader"]] = None,
        dynamic_reloading: Optional[bool] = None,
        use_env_expander: bool = True,
        use_type_casting: bool = True,
        enable_ide_support: bool = True,
        ide_stub_path: Optional[str] = None,
        debug_mode: bool = False,
        deep_merge: bool = True,
        merge_strategy: Optional[Any] = None,
        merge_strategy_map: Optional[Dict[str, Any]] = None,
        env_prefix: Optional[str] = None,
        secret_resolver: Optional[Any] = None,
        schema: Optional[Any] = None,
        validate_on_load: bool = False,
        strict_validation: bool = False,
    ) -> None:
        """Initialize the Config instance.

        Args:
            env: Environment name (e.g., 'development', 'production').
            loaders: List of configuration loaders.
            dynamic_reloading: Enable file watching for config changes.
            use_env_expander: Enable ``${VAR}`` expansion in values.
            use_type_casting: Enable automatic type casting.
            enable_ide_support: Generate IDE type stubs (default: True).
            ide_stub_path: Custom path for IDE stub file.
            debug_mode: Enable detailed source tracking.
            deep_merge: Enable deep merging of nested config (default: True).
            merge_strategy: Default ``MergeStrategy`` for combining layers.
            merge_strategy_map: Per-path merge strategy overrides.
            env_prefix: Auto-add ``EnvironmentLoader`` with this prefix.
            secret_resolver: ``SecretResolver`` for ``${secret:key}`` placeholders.
            schema: Pydantic model or JSON Schema dict for validation.
            validate_on_load: Validate immediately after loading.
            strict_validation: Raise on validation failure (vs. warn).

        Example:
            >>> from cs import Config
            >>> from cs.loaders import YamlLoader
            >>> config = Config(
            ...     env='production',
            ...     loaders=[YamlLoader('config.yaml')],
            ... )
        """
        defaults = get_default_settings()

        self.env = env or defaults["default_environment"]
        self.dynamic_reloading = (
            dynamic_reloading
            if dynamic_reloading is not None
            else defaults["dynamic_reloading"]
        )
        self.use_env_expander = use_env_expander
        self.use_type_casting = use_type_casting
        self.debug_mode = debug_mode
        self.deep_merge = deep_merge
        self.secret_resolver = secret_resolver
        self._schema = schema
        self.validate_on_load = validate_on_load
        self.strict_validation = strict_validation
        self._change_callbacks: List[Callable[..., Any]] = []
        self._validated_model: Optional[Any] = None
        self._enable_composition: bool = True
        self._lock = threading.RLock()
        self._frozen: bool = False

        # Advanced merge strategy support
        self._merge_strategy = merge_strategy
        self._merge_strategy_map = merge_strategy_map or {}
        self._advanced_merger = None
        if merge_strategy is not None:
            from config_stash.merge_strategies import AdvancedConfigMerger

            self._advanced_merger = AdvancedConfigMerger(merge_strategy)
            for path, strategy in self._merge_strategy_map.items():
                self._advanced_merger.set_strategy(path, strategy)

        # Set up loaders
        final_loaders = loaders if loaders is not None else self._load_default_files()
        if env_prefix:
            from config_stash.loaders.environment_loader import EnvironmentLoader

            final_loaders = list(final_loaders) + [EnvironmentLoader(env_prefix)]

        self.loader_manager = LoaderManager(list(final_loaders))
        self.config_loader = ConfigLoader(self.loader_manager.loaders)
        self.config_composer = ConfigComposer(
            base_path=os.getcwd(), loaders=self.loader_manager.loaders
        )
        self.file_tracker = FileTracker()
        self.version_manager: Optional[ConfigVersionManager] = None
        self.observer: Optional[ConfigObserver] = None
        self.event_emitter: Optional[ConfigEventEmitter] = None
        self.enhanced_source_tracker = EnhancedSourceTracker(debug_mode=self.debug_mode)

        # Load, merge, extract environment config
        self.configs = self._load_configs_with_tracking()
        self.merged_config = self._merge_with_tracking(self.configs)
        self.env_config = EnvironmentHandler(
            self.env, self.merged_config
        ).get_env_config()
        self._track_env_config()

        # Hooks and derived state
        self.hook_processor = HookProcessor()
        self._register_default_hooks()
        self._rebuild_state()

        if self.observer:
            self.observer.metrics.total_keys = len(self.keys())

        # File watching
        if self.dynamic_reloading:
            self.file_watcher = ConfigFileWatcher(self)
            self.file_watcher.start()

        self.config_extender = ConfigExtender(self)

        # Validation
        if self._schema and self.validate_on_load:
            self._validate_config()

        # IDE support
        self.enable_ide_support = enable_ide_support
        self.ide_stub_path = ide_stub_path
        if self.enable_ide_support:
            self._generate_ide_support()

    # -- Core methods that stay on Config directly --

    def __getattr__(self, item: str) -> Any:
        """Get configuration value using attribute-style access."""
        import time as _time

        start_time = _time.time() if self.observer else 0.0

        result = getattr(self.attribute_accessor, item)

        if self.observer:
            access_time = _time.time() - start_time
            self.observer.record_key_access(item, access_time)
            if self.event_emitter:
                self.event_emitter.emit("access", item, result)

        return result

    @property
    def typed(self) -> T:
        """Access configuration as a validated, fully-typed Pydantic model.

        Returns the validated Pydantic model instance, giving you full IDE
        autocomplete and mypy/pyright type checking on every attribute access.

        Requires ``schema`` to be a Pydantic model class and
        ``validate_on_load=True`` (or a prior call to ``validate()``).

        Returns:
            The validated Pydantic model instance of type ``T``.

        Raises:
            ValueError: If no schema was provided or validation hasn't run.

        Example:
            >>> from pydantic import BaseModel
            >>> class AppConfig(BaseModel):
            ...     database_host: str
            ...     database_port: int = 5432
            ...
            >>> config = Config[AppConfig](
            ...     loaders=[YamlLoader("config.yaml")],
            ...     schema=AppConfig,
            ...     validate_on_load=True,
            ... )
            >>> config.typed.database_host   # IDE knows: str
            >>> config.typed.database_port   # IDE knows: int
        """
        if self._validated_model is None:
            if self._schema is None:
                raise ValueError(
                    "No schema provided. Use Config[MyModel](schema=MyModel, "
                    "validate_on_load=True) for typed access."
                )
            # Auto-validate if schema exists but validation hasn't run yet
            self._validate_config()
            if self._validated_model is None:
                raise ValueError(
                    "Validation did not produce a typed model. "
                    "Ensure the schema is a Pydantic BaseModel class."
                )
        return self._validated_model

    def get_source(self, key: str) -> Optional[str]:
        """Get the source file for a configuration key."""
        return self.enhanced_source_tracker.get_source(key)

    def _rebuild_state(self) -> None:
        """Rebuild lazy_loader and attribute_accessor from env_config."""
        self.lazy_loader = LazyLoader(self.env_config)
        self.lazy_loader.clear_cache()
        self.attribute_accessor = AttributeAccessor(
            self.lazy_loader, self.hook_processor
        )

    def freeze(self) -> None:
        """Freeze configuration — ``set()`` and ``reload()`` will raise."""
        self._frozen = True

    @property
    def is_frozen(self) -> bool:
        """Whether this configuration is frozen (read-only)."""
        return self._frozen

    def _check_frozen(self) -> None:
        """Raise if config is frozen."""
        if self._frozen:
            raise RuntimeError(
                "Configuration is frozen. Create a new Config instance "
                "if you need to change configuration."
            )

    def _load_default_files(self) -> List["Loader"]:
        """Load default configuration files from pyproject.toml settings."""
        loaders: List["Loader"] = []
        default_files = get_default_settings()["default_files"]
        loader_classes = get_default_loaders()

        for file in default_files:
            ext = file.split(".")[-1]
            if ext in loader_classes:
                loaders.append(loader_classes[ext](file))
        loaders.append(loader_classes["env"](get_default_settings()["default_prefix"]))
        return loaders

    def _register_default_hooks(self) -> None:
        """Register default hooks (secrets, env expansion, type casting)."""
        if self.secret_resolver:
            self.hook_processor.register_global_hook(self.secret_resolver.hook)
        if self.use_env_expander:
            self.hook_processor.register_global_hook(EnvVarExpander.hook)
        if self.use_type_casting:
            self.hook_processor.register_global_hook(TypeCasting.hook)

    def export(self, format: str = "json", output_path: Optional[str] = None) -> str:
        """Export configuration in specified format.

        Args:
            format: Export format ('json', 'yaml', 'toml')
            output_path: Optional path to save exported config

        Returns:
            Exported configuration as string
        """
        config_dict = self.to_dict()

        if format == "json":
            import json

            output = json.dumps(config_dict, indent=2)
        elif format == "yaml":
            import yaml

            output = yaml.dump(config_dict, default_flow_style=False)
        elif format == "toml":
            from config_stash.utils.toml_compat import dumps as toml_dumps

            output = toml_dumps(config_dict)
        else:
            raise ValueError(f"Unsupported export format: {format}")

        if output_path:
            with open(output_path, "w") as f:
                f.write(output)

        return output

    @staticmethod
    def builder() -> "ConfigBuilder":
        """Create a new ConfigBuilder instance.

        Returns:
            New ConfigBuilder instance

        Example:
            >>> config = Config.builder() \\
            ...     .with_env("production") \\
            ...     .add_loader(YamlLoader("config.yaml")) \\
            ...     .build()
        """
        from config_stash.config_builder import ConfigBuilder

        return ConfigBuilder()
