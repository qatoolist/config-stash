import logging
import os
import threading
import time
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

from config_stash.attribute_accessor import AttributeAccessor
from config_stash.config_builder import ConfigBuilder
from config_stash.config_composition import ConfigComposer
from config_stash.config_diff import ConfigDiff, ConfigDiffer, ConfigDriftDetector
from config_stash.config_extender import ConfigExtender
from config_stash.config_introspection import (
    get_all_keys,
    get_nested_value,
    get_schema_info,
    has_key,
)
from config_stash.config_loader import ConfigLoader
from config_stash.config_merger import ConfigMerger
from config_stash.config_reader import get_default_loaders, get_default_settings
from config_stash.config_versioning import ConfigVersion, ConfigVersionManager
from config_stash.config_watcher import ConfigFileWatcher
from config_stash.enhanced_source_tracker import EnhancedSourceTracker, SourceInfo
from config_stash.environment_handler import EnvironmentHandler
from config_stash.exceptions import ConfigNotFoundError
from config_stash.file_tracker import FileTracker
from config_stash.hook_processor import HookProcessor
from config_stash.hooks.env_var_expander import EnvVarExpander
from config_stash.hooks.type_casting import TypeCasting
from config_stash.loader_manager import LoaderManager
from config_stash.observability import ConfigEventEmitter, ConfigObserver
from config_stash.utils.lazy_loader import LazyLoader

if TYPE_CHECKING:
    from config_stash.loaders.loader import Loader

logger = logging.getLogger(__name__)


class Config:
    """Main configuration management class for Config-Stash.

    This class provides a unified interface for loading, merging, and accessing
    configuration values from multiple sources with support for environment-specific
    configs, dynamic reloading, and hook-based transformations.

    Attributes:
        env: Current environment name
        dynamic_reloading: Whether file watching is enabled
        merged_config: The complete merged configuration dictionary
        env_config: Environment-specific configuration
    """

    def __init__(
        self,
        env: Optional[str] = None,
        loaders: Optional[List["Loader"]] = None,
        dynamic_reloading: Optional[bool] = None,
        use_env_expander: bool = True,
        use_type_casting: bool = True,
        enable_ide_support: bool = True,
        ide_stub_path: Optional[str] = None,
        debug_mode: bool = False,
        deep_merge: bool = True,
        secret_resolver: Optional[Any] = None,
        schema: Optional[Any] = None,
        validate_on_load: bool = False,
        strict_validation: bool = False,
    ) -> None:
        """Initialize the Config instance.

        Args:
            env: Environment name (e.g., 'development', 'production').
                If not provided, uses the default from pyproject.toml.
            loaders: List of configuration loaders (e.g., YamlLoader, JsonLoader).
                If not provided, uses default loaders from pyproject.toml.
            dynamic_reloading: Enable file watching for config changes.
                If not provided, uses the default from pyproject.toml.
            use_env_expander: Enable environment variable expansion in config values.
            use_type_casting: Enable automatic type casting of config values.
            enable_ide_support: Automatically generate IDE type stubs for autocomplete (default: True).
            ide_stub_path: Custom path for IDE stub file (default: .config_stash/.stubs.pyi).
            debug_mode: Enable detailed source tracking and debugging (default: False).
            deep_merge: Enable deep merging of nested configuration (default: True).
            secret_resolver: Optional SecretResolver instance for resolving secrets from
                external secret stores (AWS Secrets Manager, HashiCorp Vault, etc.).

                Example:
                    >>> from config_stash.secret_stores import AWSSecretsManager, SecretResolver
                    >>> store = AWSSecretsManager(region_name='us-east-1')
                    >>> config = Config(secret_resolver=SecretResolver(store))

            schema: Optional Pydantic model class or JSON Schema dictionary for validation.
                If provided, configuration will be validated against this schema.

                Example with Pydantic:
                    >>> from pydantic import BaseModel
                    >>> class AppConfig(BaseModel):
                    ...     database_url: str
                    >>> config = Config(schema=AppConfig, validate_on_load=True)

                Example with JSON Schema:
                    >>> schema = {"type": "object", "properties": {"database_url": {"type": "string"}}}
                    >>> config = Config(schema=schema, validate_on_load=True)
            validate_on_load: If True, validate configuration immediately after loading (default: False).
                Requires schema to be provided.
            strict_validation: If True, raise ConfigValidationError on validation failure.
                If False, log warnings but continue (default: False).

        Example:
            >>> from config_stash import Config
            >>> from config_stash.loaders import YamlLoader
            >>> config = Config(
            ...     env='production',
            ...     loaders=[YamlLoader('config.yaml')],
            ...     dynamic_reloading=True
            ... )
            >>>
            >>> # With secret store integration:
            >>> from config_stash.secret_stores import AWSSecretsManager, SecretResolver
            >>> secret_store = AWSSecretsManager(region_name='us-east-1')
            >>> config = Config(
            ...     env='production',
            ...     loaders=[YamlLoader('config.yaml')],
            ...     secret_resolver=SecretResolver(secret_store)
            ... )
        """
        defaults = get_default_settings()

        self.env = env or defaults["default_environment"]
        self.dynamic_reloading = (
            dynamic_reloading if dynamic_reloading is not None else defaults["dynamic_reloading"]
        )
        self.use_env_expander = use_env_expander
        self.use_type_casting = use_type_casting
        self.debug_mode = debug_mode
        self.deep_merge = deep_merge
        self.secret_resolver = secret_resolver
        self._schema = schema
        self.validate_on_load = validate_on_load
        self.strict_validation = strict_validation
        self._change_callbacks: List[Callable] = []
        self._validated_model: Optional[Any] = None
        self._enable_composition: bool = True  # Enable composition by default
        self._lock = threading.RLock()  # Thread safety for reload/set

        # Use default loaders only if loaders is None, not if it's an empty list
        final_loaders = loaders if loaders is not None else self._load_default_files()
        self.loader_manager = LoaderManager(final_loaders)
        self.config_loader = ConfigLoader(self.loader_manager.loaders)
        self.config_composer = ConfigComposer(
            base_path=os.getcwd(), loaders=self.loader_manager.loaders
        )
        self.file_tracker = FileTracker()
        self.version_manager: Optional[ConfigVersionManager] = None
        self.observer: Optional[ConfigObserver] = None
        self.event_emitter: Optional[ConfigEventEmitter] = None

        # Initialize enhanced source tracker
        self.enhanced_source_tracker = EnhancedSourceTracker(debug_mode=self.debug_mode)

        # Load configs and track sources
        self.configs = self._load_configs_with_tracking()
        self.merged_config = self._merge_with_tracking(self.configs)
        self.env_config = EnvironmentHandler(self.env, self.merged_config).get_env_config()

        # Track environment-extracted config for easy lookup (without environment prefix)
        self._track_env_config()

        self.hook_processor = HookProcessor()

        self._register_default_hooks()

        # Build derived state (lazy_loader, attribute_accessor)
        self._rebuild_state()

        # Update metrics with total keys if observer is enabled
        if self.observer:
            self.observer.metrics.total_keys = len(self.keys())

        if self.dynamic_reloading:
            self.file_watcher = ConfigFileWatcher(self)
            self.file_watcher.start()

        self.config_extender = ConfigExtender(self)

        # Validate configuration if schema provided and validate_on_load is True
        if self._schema and self.validate_on_load:
            self._validate_config()

        # Generate IDE support automatically
        self.enable_ide_support = enable_ide_support
        self.ide_stub_path = ide_stub_path
        if self.enable_ide_support:
            self._generate_ide_support()

    def _get_changed_loaders(self) -> Optional[List["Loader"]]:
        """Get list of loaders for files that have changed.

        Returns:
            List of loaders for changed files, or None if all should be reloaded
        """
        changed_loaders = []
        watched_files = self.get_watched_files()

        for loader in self.loader_manager.loaders:
            source_file = getattr(loader, "source", None)
            if source_file and source_file in watched_files:
                if self.file_tracker.has_changed(source_file):
                    changed_loaders.append(loader)
                    # Update tracking after detecting change
                    self.file_tracker.update_tracking(source_file)
            else:
                # Non-file loaders (e.g., EnvironmentLoader) - always reload
                changed_loaders.append(loader)

        return changed_loaders if changed_loaders else None

    def _load_configs_with_tracking(
        self, changed_loaders: Optional[List["Loader"]] = None
    ) -> List[Tuple[Dict[str, Any], str]]:
        """Load configurations with source tracking.

        Args:
            changed_loaders: Optional list of loaders to reload. If None, reload all.

        Returns:
            List of (configuration, source) tuples for compatibility with ConfigMerger
        """
        configs = []
        has_env_structure = False

        # Use changed loaders if provided, otherwise use all loaders
        loaders_to_process = changed_loaders if changed_loaders else self.loader_manager.loaders

        # First pass: load configs and check for environment structure
        for loader in loaders_to_process:
            try:
                config = loader.load()
            except Exception as e:
                # Log warning but continue with other loaders
                logger.warning(
                    f"Failed to load configuration from {getattr(loader, 'source', loader.__class__.__name__)}: {e}"
                )
                continue
            if config:
                # Process composition directives (includes, defaults) if enabled
                if self._enable_composition:
                    source_file = getattr(loader, "source", loader.__class__.__name__)
                    try:
                        config = self.config_composer.compose(config, source=source_file)
                    except Exception as e:
                        logger.warning(f"Failed to process composition in {source_file}: {e}")
                        # Continue with uncomposed config

                # Check if any config has environment structure
                if self.env and self.env in config:
                    has_env_structure = True

                source_file = getattr(loader, "source", loader.__class__.__name__)
                loader_type = loader.__class__.__name__
                configs.append((config, source_file, loader_type, loader))

        # Normalize configs: if some have environment structure and some don't,
        # wrap flat configs under the environment key
        if has_env_structure and self.env:
            normalized_configs = []
            for config, source_file, loader_type, loader in configs:
                if self.env not in config and "default" not in config:
                    # This is a flat config (e.g., from EnvironmentLoader)
                    # Wrap it under the environment key
                    normalized_config = {self.env: config}
                    normalized_configs.append((normalized_config, source_file, loader_type, loader))
                else:
                    normalized_configs.append((config, source_file, loader_type, loader))
            configs = normalized_configs

        # Second pass: track the final (possibly normalized) configs
        result = []
        for config, source_file, loader_type, loader in configs:
            # Track loader
            self.enhanced_source_tracker.track_loader(loader_type, source_file)

            # Track file for incremental reloading (if it's a file path)
            if source_file and os.path.exists(source_file):
                self.file_tracker.track_file(source_file)

            # Track individual values (always track for basic functionality,
            # debug_mode provides additional detailed tracking internally)
            self._track_config_values(config, source_file, loader_type)

            result.append((config, source_file))

        return result

    def _track_env_config(self) -> None:
        """Track environment-extracted config values for easy lookup.

        This creates tracking entries without the environment prefix,
        so `database.host` can be found even though it was tracked as `default.database.host`.
        """
        if not self.env_config or not self.env:
            return

        # Copy tracking from environment-prefixed keys to non-prefixed keys
        env_prefix = f"{self.env}."
        for key in list(self.enhanced_source_tracker.sources.keys()):
            if key.startswith(env_prefix):
                # Get the key without environment prefix
                unprefixed_key = key[len(env_prefix) :]
                # Create a new SourceInfo with the unprefixed key
                if unprefixed_key not in self.enhanced_source_tracker.sources:
                    source_info = self.enhanced_source_tracker.sources[key]
                    # Create new SourceInfo with unprefixed key but same override_count
                    self.enhanced_source_tracker.sources[unprefixed_key] = SourceInfo(
                        key=unprefixed_key,
                        value=source_info.value,
                        source_file=source_info.source_file,
                        loader_type=source_info.loader_type,
                        line_number=source_info.line_number,
                        environment=source_info.environment,
                        override_count=source_info.override_count,
                    )

                # Also alias the override history
                if key in self.enhanced_source_tracker.override_history:
                    if unprefixed_key not in self.enhanced_source_tracker.override_history:
                        self.enhanced_source_tracker.override_history[unprefixed_key] = (
                            self.enhanced_source_tracker.override_history[key]
                        )

    def _track_config_values(
        self,
        config: Dict[str, Any],
        source_file: str,
        loader_type: str,
        prefix: str = "",
    ) -> None:
        """Recursively track configuration values.

        Args:
            config: Configuration dictionary
            source_file: Source file name
            loader_type: Type of loader
            prefix: Key prefix for nested values
        """
        for key, value in config.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                # Track the dict itself
                self.enhanced_source_tracker.track_value(
                    full_key,
                    value,
                    source_file,
                    loader_type,
                    environment=self.env if key == self.env else None,
                )
                # Recursively track nested values
                self._track_config_values(value, source_file, loader_type, full_key)
            else:
                # Track leaf value
                self.enhanced_source_tracker.track_value(
                    full_key,
                    value,
                    source_file,
                    loader_type,
                    environment=self.env if self.env and prefix.startswith(self.env) else None,
                )

    def _merge_with_tracking(self, configs: List[Tuple[Dict[str, Any], str]]) -> Dict[str, Any]:
        """Merge configurations while tracking overrides.

        Args:
            configs: List of (configuration, source) tuples

        Returns:
            Merged configuration dictionary
        """
        # Tracking is already done in _load_configs_with_tracking
        # No need to re-track here as it would increment override counts incorrectly
        merged = ConfigMerger.merge_configs(configs, deep_merge=self.deep_merge)
        return merged

    def _generate_ide_support(self) -> None:
        """Automatically generate IDE type stubs for autocomplete."""
        try:
            import os

            from config_stash.ide_support import IDESupport

            # Determine stub file path
            if self.ide_stub_path is None:
                # Create a .config_stash directory for IDE files
                ide_dir = ".config_stash"
                if not os.path.exists(ide_dir):
                    os.makedirs(ide_dir)
                stub_path = os.path.join(ide_dir, "stubs.pyi")

                # Also create an __init__.py to make it importable
                init_path = os.path.join(ide_dir, "__init__.py")
                with open(init_path, "w") as f:
                    f.write("# Auto-generated by Config-Stash for IDE support\n")
                    f.write("from .stubs import ConfigType\n")
                    f.write("__all__ = ['ConfigType']\n")
            else:
                stub_path = self.ide_stub_path
                # Ensure parent directory exists
                stub_dir = os.path.dirname(stub_path)
                if stub_dir and not os.path.exists(stub_dir):
                    os.makedirs(stub_dir)

            # Generate the stub file
            IDESupport.generate_stub(self, stub_path, silent=True)

            # If dynamic reloading is enabled, auto-update stubs
            if self.dynamic_reloading:

                @self.on_change
                def _update_ide_stubs(key: str, old_value, new_value):
                    if isinstance(new_value, dict) or old_value is None:
                        IDESupport.generate_stub(self, stub_path, silent=True)

        except Exception as e:
            # Don't fail Config initialization if IDE support fails
            logger.debug(f"IDE support generation skipped: {e}")

    def _load_default_files(self) -> List:
        """Load default configuration files based on pyproject.toml settings.

        Returns:
            List of loader instances for default configuration files
        """
        loaders = []
        default_files = get_default_settings()["default_files"]
        loader_classes = get_default_loaders()

        for file in default_files:
            ext = file.split(".")[-1]
            if ext in loader_classes:
                loaders.append(loader_classes[ext](file))
        loaders.append(loader_classes["env"](get_default_settings()["default_prefix"]))

        return loaders

    def _register_default_hooks(self) -> None:
        """Register default hooks based on configuration settings.

        Hook execution order:
        1. Secret resolver (if configured) - resolves ${secret:key} placeholders
        2. Environment variable expander - resolves ${VAR_NAME} placeholders
        3. Type casting - converts string values to appropriate types
        """
        # Register secret resolver first so secrets are resolved before env vars
        if self.secret_resolver:
            self.hook_processor.register_global_hook(self.secret_resolver.hook)

        if self.use_env_expander:
            self.hook_processor.register_global_hook(EnvVarExpander.hook)

        if self.use_type_casting:
            self.hook_processor.register_global_hook(TypeCasting.hook)

    def _rebuild_state(self) -> None:
        """Rebuild derived state from env_config.

        This is the single point for rebuilding lazy_loader and
        attribute_accessor. Call after any mutation of env_config.
        """
        self.lazy_loader = LazyLoader(self.env_config)
        self.lazy_loader.clear_cache()
        self.attribute_accessor = AttributeAccessor(self.lazy_loader, self.hook_processor)

    def __getattr__(self, item: str) -> Any:
        """Get configuration value using attribute-style access.

        Args:
            item: Configuration key to retrieve

        Returns:
            Configuration value after processing through hooks

        Example:
            >>> config.database.host  # Instead of config['database']['host']
        """
        # Record access metrics if observer is enabled
        start_time = time.time() if self.observer else 0.0

        result = getattr(self.attribute_accessor, item)

        # Record access
        if self.observer:
            access_time = time.time() - start_time
            self.observer.record_key_access(item, access_time)
            if self.event_emitter:
                self.event_emitter.emit("access", item, result)

        return result

    def get_source(self, key: str) -> Optional[str]:
        """Get the source file for a configuration key.

        Args:
            key: Configuration key to look up

        Returns:
            Path to the source file containing this key, or None if not found
        """
        # Use enhanced source tracker for better tracking
        return self.enhanced_source_tracker.get_source(key)

    def reload(
        self,
        validate: Optional[bool] = None,
        dry_run: bool = False,
        incremental: bool = True,
    ) -> None:
        """Reload configuration from all sources.

        This method re-reads all configuration files and updates the
        merged configuration. Useful when files have been modified.

        Args:
            validate: Optional flag to validate after reload. If None,
                     uses validate_on_load from initialization.
            dry_run: If True, validate without applying changes (default: False)
            incremental: If True, only reload changed files (default: True).
                        If False, reload all files regardless of changes.

        Raises:
            ConfigValidationError: If validation fails and strict_validation is True

        Example:
            >>> config.reload(validate=True)  # Reload and validate
            >>> config.reload(dry_run=True)   # Test reload without applying
            >>> config.reload(incremental=False)  # Force full reload
        """
        with self._lock:
            self._reload_internal(validate, dry_run, incremental)

    def _reload_internal(
        self,
        validate: Optional[bool] = None,
        dry_run: bool = False,
        incremental: bool = True,
    ) -> None:
        """Internal reload implementation (called under lock)."""
        logger.info("Reloading configuration...")
        old_config = self.env_config.copy() if self.env_config else {}

        # Determine which loaders need to be reloaded
        if incremental:
            changed_loaders = self._get_changed_loaders()
            if not changed_loaders:
                logger.info("No configuration files changed, skipping reload")
                return
            logger.info(f"Reloading {len(changed_loaders)} changed file(s)")
        else:
            changed_loaders = None  # Reload all

        # Record reload start time for metrics
        reload_start = time.time()

        # Save state for dry_run restoration
        old_configs = self.configs
        old_merged_config = self.merged_config

        # Reload configurations
        if incremental and changed_loaders:
            # Incremental reload: reload only changed files
            # We need to replace configs from changed loaders in the existing configs list
            changed_sources = {getattr(loader, "source", None) for loader in changed_loaders}
            # Filter out configs from changed sources
            existing_configs = [
                (config, source) for config, source in self.configs if source not in changed_sources
            ]
            # Load new configs from changed loaders
            new_configs = self._load_configs_with_tracking(changed_loaders=changed_loaders)
            # Combine: existing unchanged + new changed
            self.configs = existing_configs + new_configs
        else:
            # Full reload: reload all configs
            self.configs = self._load_configs_with_tracking()

        self.merged_config = self._merge_with_tracking(self.configs)
        new_env_config = EnvironmentHandler(self.env, self.merged_config).get_env_config()

        # Record reload duration
        reload_duration = time.time() - reload_start
        if self.observer:
            self.observer.record_reload(reload_duration)
        if self.event_emitter:
            self.event_emitter.emit("reload", new_env_config, reload_duration)

        # Validate if requested
        should_validate = validate if validate is not None else self.validate_on_load
        if should_validate and self._schema:
            # Temporarily set env_config for validation
            temp_env_config = self.env_config
            self.env_config = new_env_config
            try:
                self._validate_config()
            except Exception as e:
                # Restore old config on validation failure
                self.env_config = temp_env_config
                raise

        # Dry run - don't apply changes, restore all state
        if dry_run:
            self.configs = old_configs
            self.merged_config = old_merged_config
            if should_validate and self._schema:
                self.env_config = temp_env_config
            logger.info("Dry run completed - changes not applied")
            return

        self.env_config = new_env_config
        self._rebuild_state()

        # Trigger change callbacks
        self._trigger_change_callbacks(old_config, self.env_config)

        # Record change in metrics
        if self.observer:
            self.observer.record_change()
        if self.event_emitter:
            self.event_emitter.emit("change", old_config, self.env_config)

    def get_watched_files(self) -> List[str]:
        """Get list of files being watched for changes.

        Returns:
            List of file paths being monitored
        """
        files = []
        for loader in self.loader_manager.loaders:
            if hasattr(loader, "source"):
                files.append(loader.source)
        return files

    def stop_watching(self) -> None:
        """Stop watching configuration files for changes."""
        if self.dynamic_reloading:
            self.file_watcher.stop()

    def extend(self, loader: Any) -> None:
        """Extend configuration with an additional loader.

        Args:
            loader: Configuration loader instance to add
        """
        self.config_extender.extend_config(loader)

    def register_key_hook(self, key: str, hook: Callable[[Any], Any]) -> None:
        """Register a hook for a specific configuration key.

        Args:
            key: Configuration key to attach the hook to
            hook: Callable that transforms the configuration value
        """
        self.hook_processor.register_key_hook(key, hook)

    def register_value_hook(self, value: Any, hook: Callable[[Any], Any]) -> None:
        """Register a hook for a specific value.

        Args:
            value: Configuration value to attach the hook to
            hook: Callable that transforms the configuration value
        """
        self.hook_processor.register_value_hook(value, hook)

    def register_condition_hook(
        self, condition: Callable[[str, Any], bool], hook: Callable[[Any], Any]
    ) -> None:
        """Register a hook that runs when a condition is met.

        Args:
            condition: Callable that returns True when hook should run
            hook: Callable that transforms the configuration value
        """
        self.hook_processor.register_condition_hook(condition, hook)

    def register_global_hook(self, hook: Callable[[Any], Any]) -> None:
        """Register a hook that runs for all configuration values.

        Args:
            hook: Callable that transforms the configuration value
        """
        self.hook_processor.register_global_hook(hook)

    def get_source_info(self, key: str) -> Optional[SourceInfo]:
        """Get detailed source information for a configuration key.

        Args:
            key: Configuration key (dot notation)

        Returns:
            SourceInfo object with detailed tracking information, or None if not found
        """
        return self.enhanced_source_tracker.get_source_info(key)

    def get_override_history(self, key: str) -> List[SourceInfo]:
        """Get the history of overrides for a configuration key.

        Args:
            key: Configuration key (dot notation)

        Returns:
            List of SourceInfo objects showing all values that were overridden
        """
        return self.enhanced_source_tracker.get_override_history(key)

    def print_debug_info(self, key: Optional[str] = None) -> None:
        """Print debug information about configuration sources.

        Args:
            key: Optional specific key to debug, or None for all keys
        """
        self.enhanced_source_tracker.print_debug_info(key)

    def export_debug_report(self, output_path: str = "config_debug_report.json") -> None:
        """Export a detailed debug report to a JSON file.

        Args:
            output_path: Path to output JSON file
        """
        self.enhanced_source_tracker.export_debug_report(output_path)

    def find_keys_from_source(self, source_pattern: str) -> List[str]:
        """Find all configuration keys that came from a specific source.

        Args:
            source_pattern: Source file pattern to search for

        Returns:
            List of configuration keys from matching sources
        """
        return self.enhanced_source_tracker.find_keys_from_source(source_pattern)

    def get_source_statistics(self) -> Dict[str, Any]:
        """Get statistics about configuration sources.

        Returns:
            Dictionary with detailed source statistics
        """
        return self.enhanced_source_tracker.get_source_statistics()

    def get_conflicts(self) -> Dict[str, List[SourceInfo]]:
        """Get all configuration keys that have been overridden.

        Returns:
            Dictionary mapping keys to their override history
        """
        return self.enhanced_source_tracker.get_conflicts()

    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary.

        Returns:
            The current configuration as a dictionary
        """
        # Return env_config if it has data, otherwise merged_config
        return self.env_config if self.env_config else self.merged_config

    def keys(self, prefix: str = "") -> List[str]:
        """Get all configuration keys.

        Args:
            prefix: Optional prefix to filter keys (e.g., "database" for nested keys)

        Returns:
            List of dot-separated key paths

        Example:
            >>> config.keys()
            ['database', 'database.host', 'database.port', 'app']
            >>> config.keys(prefix="database")
            ['database.host', 'database.port']
        """
        config_dict = self.to_dict()
        all_keys = get_all_keys(config_dict, "")
        if prefix:
            # Filter keys that start with prefix
            filtered_keys = [k for k in all_keys if k.startswith(prefix)]
            # Remove prefix from keys
            if prefix and not prefix.endswith("."):
                prefix = prefix + "."
            return [k[len(prefix) :] if k.startswith(prefix) else k for k in filtered_keys]
        return all_keys

    def has(self, key_path: str) -> bool:
        """Check if a configuration key exists.

        Args:
            key_path: Dot-separated key path (e.g., "database.host")

        Returns:
            True if key exists, False otherwise

        Example:
            >>> config.has("database.host")
            True
            >>> config.has("database.port")
            False
        """
        config_dict = self.to_dict()
        return has_key(config_dict, key_path)

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get a configuration value by key path with optional default.

        Args:
            key_path: Dot-separated key path (e.g., "database.host")
            default: Default value if key not found

        Returns:
            Configuration value or default if not found

        Example:
            >>> config.get("database.host", "localhost")
            'db.example.com'
            >>> config.get("database.port", 5432)
            5432
        """
        config_dict = self.to_dict()
        value = get_nested_value(config_dict, key_path, default)
        # Apply hooks if hook processor is available
        if self.hook_processor and value is not None:
            value = self.hook_processor.process_hooks(key_path, value)
        return value

    def schema(self, key_path: str = "") -> Dict[str, Any]:
        """Get schema information for a configuration key or entire config.

        Args:
            key_path: Optional dot-separated key path. If empty, returns schema for entire config.

        Returns:
            Dictionary with schema information (type, keys, nested structure, etc.)

        Example:
            >>> schema = config.schema("database")
            >>> schema["type"]  # 'dict'
            >>> schema["keys"]  # ['host', 'port']
            >>> schema = config.schema()  # Entire config schema
        """
        config_dict = self.to_dict()
        schema_info = get_schema_info(config_dict, key_path)

        # Add type information from validated model if available
        if self._validated_model and hasattr(self._validated_model, "model_json_schema"):
            # If we have a validated Pydantic model, include schema info
            try:
                pydantic_schema = self._validated_model.model_json_schema()
                schema_info["pydantic_schema"] = pydantic_schema
            except Exception:
                pass

        return schema_info

    def explain(self, key_path: str) -> Dict[str, Any]:
        """Explain how a configuration key was resolved.

        This provides detailed information about where a key came from,
        its value, source file, override history, and resolution path.

        Args:
            key_path: Dot-separated key path (e.g., "database.host")

        Returns:
            Dictionary with detailed resolution information

        Example:
            >>> info = config.explain("database.host")
            >>> info["value"]  # 'localhost'
            >>> info["source"]  # 'config/base.yaml'
            >>> info["override_count"]  # 2
        """
        info: Dict[str, Any] = {}

        # Get source information
        source_info = self.get_source_info(key_path)
        if source_info:
            info["value"] = source_info.value
            info["source"] = source_info.source_file
            info["loader_type"] = source_info.loader_type
            info["environment"] = source_info.environment
            info["override_count"] = source_info.override_count
        else:
            # Key doesn't exist
            info["exists"] = False
            info["available_keys"] = self.keys()
            return info

        # Get override history
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

        # Get schema information (use method, not attribute)
        info["schema"] = self.schema(key_path)

        # Get current value
        config_dict = self.to_dict()
        info["current_value"] = get_nested_value(config_dict, key_path)

        return info

    def diff(self, other: "Config") -> List[ConfigDiff]:
        """Compare this configuration with another configuration.

        Args:
            other: Another Config instance to compare with

        Returns:
            List of ConfigDiff objects representing all differences

        Example:
            >>> config1 = Config(env="dev", loaders=[YamlLoader("dev.yaml")])
            >>> config2 = Config(env="prod", loaders=[YamlLoader("prod.yaml")])
            >>> diffs = config1.diff(config2)
            >>> for diff in diffs:
            ...     print(f"{diff.path}: {diff.diff_type.value}")
        """
        dict1 = self.to_dict()
        dict2 = other.to_dict()
        return ConfigDiffer.diff(dict1, dict2)

    def detect_drift(self, intended_config: "Config") -> List[ConfigDiff]:
        """Detect configuration drift (actual vs. intended state).

        This method compares the current configuration with an intended
        configuration to detect any drift or unauthorized changes.

        Args:
            intended_config: Config instance representing intended state

        Returns:
            List of ConfigDiff objects representing drift

        Example:
            >>> intended = Config(loaders=[YamlLoader("intended.yaml")])
            >>> actual = Config(loaders=[YamlLoader("actual.yaml")])
            >>> drift = actual.detect_drift(intended)
            >>> if drift:
            ...     print(f"Configuration drift detected: {len(drift)} differences")
        """
        detector = ConfigDriftDetector(intended_config.to_dict())
        return detector.detect_drift(self.to_dict())

    def set(self, key_path: str, value: Any, override: bool = True) -> None:
        """Set a configuration value programmatically.

        This method allows you to override configuration values after
        initialization, which is useful for dynamic configuration updates.

        Args:
            key_path: Dot-separated key path (e.g., "database.host")
            value: Value to set
            override: If True, override existing value. If False, only set if not exists.

        Raises:
            ConfigNotFoundError: If key path is invalid or override=False and key exists

        Example:
            >>> config.set("database.host", "new-host.example.com")
            >>> config.set("app.debug", True, override=True)
            >>> # Set nested value
            >>> config.set("database.connection.timeout", 30)
        """
        with self._lock:
            self._set_internal(key_path, value, override)

    def _set_internal(self, key_path: str, value: Any, override: bool = True) -> None:
        """Internal set implementation (called under lock)."""
        config_dict = self.to_dict()
        keys = key_path.split(".")
        current = config_dict

        # Navigate to the parent dictionary
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

        # Check if key already exists
        final_key = keys[-1]
        if final_key in current and not override:
            raise ConfigNotFoundError(
                f"Key '{key_path}' already exists. Use override=True to replace it.",
                key=key_path,
            )

        # Set the value
        current[final_key] = value

        # Update internal state
        if self.env_config:
            # Update env_config
            env_current = self.env_config
            for key in keys[:-1]:
                if key not in env_current:
                    env_current[key] = {}
                elif not isinstance(env_current[key], dict):
                    env_current[key] = {}
                env_current = env_current[key]
            env_current[final_key] = value

            # Also update merged_config to keep state consistent
            from config_stash.utils.dict_utils import set_nested

            set_nested(self.merged_config, key_path, value)

            # Rebuild derived state
            self._rebuild_state()

        logger.info(f"Set configuration key '{key_path}' = {value}")

        # Record change
        if self.observer:
            self.observer.record_change()
        if self.event_emitter:
            self.event_emitter.emit("set", key_path, value)

    def enable_observability(self) -> ConfigObserver:
        """Enable observability and metrics collection.

        Returns:
            ConfigObserver instance for accessing metrics

        Example:
            >>> observer = config.enable_observability()
            >>> # ... use config ...
            >>> stats = observer.get_statistics()
            >>> print(f"Config accessed {stats['accessed_keys']} times")
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

        Example:
            >>> metrics = config.get_metrics()
            >>> if metrics:
            ...     print(f"Reload count: {metrics['reload_count']}")
        """
        if self.observer:
            return self.observer.get_statistics()
        return None

    def enable_versioning(self, storage_path: Optional[str] = None) -> ConfigVersionManager:
        """Enable configuration versioning.

        Args:
            storage_path: Optional path to store version history

        Returns:
            ConfigVersionManager instance

        Example:
            >>> manager = config.enable_versioning()
            >>> version = manager.save_version(config.to_dict())
        """
        self.version_manager = ConfigVersionManager(storage_path=storage_path)
        return self.version_manager

    def save_version(self, metadata: Optional[Dict[str, Any]] = None) -> Optional[ConfigVersion]:
        """Save current configuration as a version.

        Args:
            metadata: Optional metadata (e.g., author, message)

        Returns:
            ConfigVersion instance if versioning is enabled, None otherwise

        Example:
            >>> version = config.save_version(metadata={"author": "user@example.com"})
            >>> print(f"Saved version: {version.version_id}")
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
            ConfigVersion instance, or None if not found or versioning not enabled
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

        Example:
            >>> config.rollback_to_version("abc123")
            >>> # Configuration is now restored to version abc123
        """
        if not self.version_manager:
            raise ValueError("Versioning not enabled. Call enable_versioning() first.")

        config_dict = self.version_manager.rollback(version_id)

        # Restore configuration
        self.env_config = config_dict
        self.merged_config = config_dict
        self._rebuild_state()

        logger.info(f"Configuration rolled back to version: {version_id}")

    def on_change(self, func: Callable[[str, Any, Any], None]) -> Callable:
        """Decorator to register a callback for configuration changes.

        The callback will be called with (key, old_value, new_value) when
        configuration values change during reload.

        Args:
            func: Callback function with signature (key: str, old_value: Any, new_value: Any)

        Returns:
            The decorated function

        Example:
            >>> @config.on_change
            ... def handle_change(key: str, old_value: Any, new_value: Any):
            ...     print(f"Config {key} changed from {old_value} to {new_value}")
        """
        self._change_callbacks.append(func)
        return func

    def _trigger_change_callbacks(
        self, old_config: Dict[str, Any], new_config: Dict[str, Any]
    ) -> None:
        """Trigger registered change callbacks for modified values.

        Args:
            old_config: Previous configuration
            new_config: New configuration
        """
        # Find all changed keys
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

    def _validate_config(self) -> None:
        """Validate configuration against the provided schema.

        This is called automatically if validate_on_load is True.

        Raises:
            ConfigValidationError: If validation fails and strict_validation is True
        """
        if not self._schema:
            return

        config_dict = self.env_config if self.env_config else self.merged_config

        try:
            # Check if schema is a Pydantic model class
            if hasattr(self._schema, "__bases__") and any(
                "BaseModel" in str(base) for base in self._schema.__bases__
            ):
                # Pydantic model validation
                from config_stash.validators.pydantic_validator import PydanticValidator

                validator = PydanticValidator(self._schema)
                self._validated_model = validator.validate(config_dict)
                logger.info("Configuration validated successfully against Pydantic model")
            elif isinstance(self._schema, dict):
                # JSON Schema validation
                from config_stash.validators.schema_validator import SchemaValidator

                validator = SchemaValidator(self._schema)
                validator.validate(config_dict)
                logger.info("Configuration validated successfully against JSON Schema")
            else:
                logger.warning(f"Unknown schema type: {type(self._schema)}")
        except Exception as e:
            error_msg = f"Configuration validation failed: {e}"
            if self.strict_validation:
                from config_stash.exceptions import ConfigValidationError

                # Extract detailed error information
                validation_errors = []
                if hasattr(e, "errors"):
                    validation_errors = list(e.errors())
                elif hasattr(e, "message"):
                    validation_errors = [{"message": str(e.message)}]

                raise ConfigValidationError(
                    error_msg,
                    schema_path=None,
                    validation_errors=validation_errors,
                    original_error=e,
                ) from e
            else:
                logger.warning(error_msg)

    def validate(self, schema: Optional[Any] = None) -> bool:
        """Validate configuration against a schema.

        Args:
            schema: Optional schema to validate against. If not provided,
                   uses the schema provided during Config initialization.
                   Can be a Pydantic model class or JSON Schema dictionary.

        Returns:
            True if valid, False otherwise

        Raises:
            ConfigValidationError: If validation fails and strict_validation is True

        Example:
            >>> from pydantic import BaseModel
            >>> class AppConfig(BaseModel):
            ...     database_url: str
            >>> config = Config(loaders=[YamlLoader("config.yaml")])
            >>> is_valid = config.validate(schema=AppConfig)
            >>> # Or use the schema from initialization
            >>> config = Config(schema=AppConfig, validate_on_load=True)
        """
        # Basic validation - check if config exists
        if not self.env_config and not self.merged_config:
            return False

        # Use provided schema or fall back to instance schema
        validation_schema = schema or self._schema

        if not validation_schema:
            # No schema provided - just check if config exists
            return True

        # Temporarily set schema for validation
        original_schema = self._schema
        original_validate_on_load = self.validate_on_load
        original_strict = self.strict_validation

        try:
            self._schema = validation_schema
            self.validate_on_load = True
            self.strict_validation = True
            self._validate_config()
            return True
        except Exception:
            return False
        finally:
            # Restore original values
            self._schema = original_schema
            self.validate_on_load = original_validate_on_load
            self.strict_validation = original_strict

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

        This is a convenience method for creating a builder with a fluent API.

        Returns:
            New ConfigBuilder instance

        Example:
            >>> from config_stash import Config
            >>> config = Config.builder() \\
            ...     .with_env("production") \\
            ...     .add_loader(YamlLoader("config.yaml")) \\
            ...     .enable_debug() \\
            ...     .build()
        """
        from config_stash.config_builder import ConfigBuilder

        return ConfigBuilder()
