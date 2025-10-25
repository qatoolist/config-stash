import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from config_stash.attribute_accessor import AttributeAccessor
from config_stash.config_extender import ConfigExtender
from config_stash.config_loader import ConfigLoader
from config_stash.config_merger import ConfigMerger
from config_stash.config_reader import get_default_loaders, get_default_settings
from config_stash.config_watcher import ConfigFileWatcher
from config_stash.enhanced_source_tracker import EnhancedSourceTracker, SourceInfo
from config_stash.environment_handler import EnvironmentHandler
from config_stash.hook_processor import HookProcessor
from config_stash.hooks.env_var_expander import EnvVarExpander
from config_stash.hooks.type_casting import TypeCasting
from config_stash.loader_manager import LoaderManager
from config_stash.source_tracker import SourceTracker
from config_stash.utils.lazy_loader import LazyLoader

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
        loaders: Optional[List] = None,
        dynamic_reloading: Optional[bool] = None,
        use_env_expander: bool = True,
        use_type_casting: bool = True,
        enable_ide_support: bool = True,
        ide_stub_path: Optional[str] = None,
        debug_mode: bool = False,
        deep_merge: bool = True,
        secret_resolver: Optional[Any] = None,
    ) -> None:
        """Initialize the Config instance.

        Args:
            env: Environment name (e.g., 'development', 'production').
                If not provided, uses the default from pyproject.toml.
            loaders: List of configuration loaders. If not provided,
                uses default loaders from pyproject.toml.
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
                    from config_stash.secret_stores import AWSSecretsManager, SecretResolver
                    store = AWSSecretsManager(region_name='us-east-1')
                    config = Config(secret_resolver=SecretResolver(store))

        Example:
            >>> from config_stash import Config
            >>> from config_stash.loaders import YAMLLoader
            >>> config = Config(
            ...     env='production',
            ...     loaders=[YAMLLoader('config.yaml')],
            ...     dynamic_reloading=True
            ... )
            >>>
            >>> # With secret store integration:
            >>> from config_stash.secret_stores import AWSSecretsManager, SecretResolver
            >>> secret_store = AWSSecretsManager(region_name='us-east-1')
            >>> config = Config(
            ...     env='production',
            ...     loaders=[YAMLLoader('config.yaml')],
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
        self._change_callbacks: List[Callable] = []

        self.loader_manager = LoaderManager(loaders or self._load_default_files())
        self.config_loader = ConfigLoader(self.loader_manager.loaders)

        # Initialize enhanced source tracker
        self.enhanced_source_tracker = EnhancedSourceTracker(debug_mode=self.debug_mode)

        # Load configs and track sources
        self.configs = self._load_configs_with_tracking()
        self.merged_config = self._merge_with_tracking(self.configs)
        self.env_config = EnvironmentHandler(self.env, self.merged_config).get_env_config()

        # Track environment-extracted config for easy lookup (without environment prefix)
        self._track_env_config()

        self.lazy_loader = LazyLoader(self.env_config)

        # Keep legacy source tracker for backward compatibility
        self.source_tracker = SourceTracker(self.loader_manager.loaders)
        self.hook_processor = HookProcessor()

        self._register_default_hooks()

        # Create attribute accessor with hook processor (after hooks are registered)
        self.attribute_accessor = AttributeAccessor(self.lazy_loader, self.hook_processor)

        if self.dynamic_reloading:
            self.file_watcher = ConfigFileWatcher(self)
            self.file_watcher.start()

        self.config_extender = ConfigExtender(self)

        # Generate IDE support automatically
        self.enable_ide_support = enable_ide_support
        self.ide_stub_path = ide_stub_path
        if self.enable_ide_support:
            self._generate_ide_support()

    def _load_configs_with_tracking(self) -> List[Tuple[Dict[str, Any], str]]:
        """Load configurations with source tracking.

        Returns:
            List of (configuration, source) tuples for compatibility with ConfigMerger
        """
        configs = []
        has_env_structure = False

        # First pass: load configs and check for environment structure
        for loader in self.loader_manager.loaders:
            config = loader.load()
            if config:
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
                unprefixed_key = key[len(env_prefix):]
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
                        self.enhanced_source_tracker.override_history[unprefixed_key] = self.enhanced_source_tracker.override_history[key]

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
                    environment=self.env if prefix.startswith(self.env) else None,
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

    def __getattr__(self, item: str) -> Any:
        """Get configuration value using attribute-style access.

        Args:
            item: Configuration key to retrieve

        Returns:
            Configuration value after processing through hooks

        Example:
            >>> config.database.host  # Instead of config['database']['host']
        """
        value = getattr(self.attribute_accessor, item)
        return self.hook_processor.process_hooks(item, value)

    def get_source(self, key: str) -> Optional[str]:
        """Get the source file for a configuration key.

        Args:
            key: Configuration key to look up

        Returns:
            Path to the source file containing this key, or None if not found
        """
        # Use enhanced source tracker for better tracking
        return self.enhanced_source_tracker.get_source(key)

    def reload(self) -> None:
        """Reload configuration from all sources.

        This method re-reads all configuration files and updates the
        merged configuration. Useful when files have been modified.
        """
        logger.info("Reloading configuration...")
        old_config = self.env_config.copy() if self.env_config else {}

        self.configs = self._load_configs_with_tracking()
        self.merged_config = self._merge_with_tracking(self.configs)
        self.env_config = EnvironmentHandler(self.env, self.merged_config).get_env_config()
        self.lazy_loader = LazyLoader(self.env_config)
        self.lazy_loader.clear_cache()  # Clear cache after reload
        self.attribute_accessor = AttributeAccessor(self.lazy_loader)

        # Trigger change callbacks
        self._trigger_change_callbacks(old_config, self.env_config)

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

    def validate(self, schema: Optional[Dict[str, Any]] = None) -> bool:
        """Validate configuration against a schema.

        Args:
            schema: Optional schema to validate against

        Returns:
            True if valid, False otherwise
        """
        # Basic validation - can be extended with schema validation
        if not self.env_config and not self.merged_config:
            return False
        return True

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
            import toml

            output = toml.dumps(config_dict)
        else:
            raise ValueError(f"Unsupported export format: {format}")

        if output_path:
            with open(output_path, "w") as f:
                f.write(output)

        return output
