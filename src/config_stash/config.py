import logging
from typing import Any, Callable, List, Optional

from config_stash.attribute_accessor import AttributeAccessor
from config_stash.config_extender import ConfigExtender
from config_stash.config_loader import ConfigLoader
from config_stash.config_merger import ConfigMerger
from config_stash.config_reader import get_default_loaders, get_default_settings
from config_stash.config_watcher import ConfigFileWatcher
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

        Example:
            >>> from config_stash import Config
            >>> from config_stash.loaders import YAMLLoader
            >>> config = Config(
            ...     env='production',
            ...     loaders=[YAMLLoader('config.yaml')],
            ...     dynamic_reloading=True
            ... )
        """
        defaults = get_default_settings()

        self.env = env or defaults["default_environment"]
        self.dynamic_reloading = (
            dynamic_reloading if dynamic_reloading is not None else defaults["dynamic_reloading"]
        )
        self.use_env_expander = use_env_expander
        self.use_type_casting = use_type_casting

        self.loader_manager = LoaderManager(loaders or self._load_default_files())
        self.config_loader = ConfigLoader(self.loader_manager.loaders)
        self.configs = self.config_loader.load_configs()
        self.merged_config = ConfigMerger.merge_configs(self.configs)
        self.env_config = EnvironmentHandler(self.env, self.merged_config).get_env_config()
        self.lazy_loader = LazyLoader(self.env_config)
        self.attribute_accessor = AttributeAccessor(self.lazy_loader)
        self.source_tracker = SourceTracker(self.loader_manager.loaders)
        self.hook_processor = HookProcessor()

        self._register_default_hooks()

        if self.dynamic_reloading:
            self.file_watcher = ConfigFileWatcher(self)
            self.file_watcher.start()

        self.config_extender = ConfigExtender(self)

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
        """Register default hooks based on configuration settings."""
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
        return self.source_tracker.get_source(key)

    def reload(self) -> None:
        """Reload configuration from all sources.

        This method re-reads all configuration files and updates the
        merged configuration. Useful when files have been modified.
        """
        logger.info("Reloading configuration...")
        self.configs = self.config_loader.load_configs()
        self.merged_config = ConfigMerger.merge_configs(self.configs)
        self.env_config = EnvironmentHandler(self.env, self.merged_config).get_env_config()
        self.lazy_loader = LazyLoader(self.env_config)
        self.lazy_loader.clear_cache()  # Clear cache after reload
        self.attribute_accessor = AttributeAccessor(self.lazy_loader)

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
