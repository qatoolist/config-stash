"""Configuration builder pattern for Config-Stash.

This module provides a fluent builder interface for creating Config instances,
making it easier to configure complex setup scenarios with better readability.
"""

from typing import TYPE_CHECKING, Any, List, Optional

if TYPE_CHECKING:
    from config_stash.config import Config
    from config_stash.loaders.loader import Loader
    from config_stash.secret_stores.resolver import SecretResolver


class ConfigBuilder:
    """Fluent builder for creating Config instances.

    This class provides a builder pattern for constructing Config instances
    with better readability and easier configuration management.

    Example:
        >>> builder = ConfigBuilder()
        >>> config = builder \
        ...     .with_env("production") \
        ...     .add_loader(YamlLoader("base.yaml")) \
        ...     .add_loader(YamlLoader("production.yaml")) \
        ...     .with_secrets(secret_resolver) \
        ...     .enable_debug() \
        ...     .enable_dynamic_reloading() \
        ...     .build()
    """

    def __init__(self) -> None:
        """Initialize a new ConfigBuilder with default values."""
        self._env: Optional[str] = None
        self._loaders: List["Loader"] = []
        self._dynamic_reloading: Optional[bool] = None
        self._use_env_expander: bool = True
        self._use_type_casting: bool = True
        self._enable_ide_support: bool = True
        self._ide_stub_path: Optional[str] = None
        self._debug_mode: bool = False
        self._deep_merge: bool = True
        self._secret_resolver: Optional["SecretResolver"] = None
        self._schema: Optional[Any] = None
        self._validate_on_load: bool = False
        self._strict_validation: bool = False

    def with_env(self, env: str) -> "ConfigBuilder":
        """Set the environment name.

        Args:
            env: Environment name (e.g., 'development', 'production', 'staging')

        Returns:
            Self for method chaining

        Example:
            >>> builder.with_env("production")
        """
        self._env = env
        return self

    def add_loader(self, loader: "Loader") -> "ConfigBuilder":
        """Add a configuration loader.

        Args:
            loader: Configuration loader instance to add (e.g., YamlLoader, JsonLoader)

        Returns:
            Self for method chaining

        Example:
            >>> builder.add_loader(YamlLoader("config.yaml"))
        """
        self._loaders.append(loader)
        return self

    def add_loaders(self, loaders: List["Loader"]) -> "ConfigBuilder":
        """Add multiple configuration loaders at once.

        Args:
            loaders: List of Loader instances to add

        Returns:
            Self for method chaining

        Example:
            >>> builder.add_loaders([
            ...     YamlLoader("base.yaml"),
            ...     JsonLoader("overrides.json"),
            ... ])
        """
        self._loaders.extend(loaders)
        return self

    def with_secrets(self, secret_resolver: "SecretResolver") -> "ConfigBuilder":
        """Configure secret resolver for secret store integration.

        Args:
            secret_resolver: SecretResolver instance for resolving secrets

        Returns:
            Self for method chaining

        Example:
            >>> from config_stash.secret_stores import AWSSecretsManager, SecretResolver
            >>> store = AWSSecretsManager(region_name='us-east-1')
            >>> builder.with_secrets(SecretResolver(store))
        """
        self._secret_resolver = secret_resolver
        return self

    def enable_dynamic_reloading(self) -> "ConfigBuilder":
        """Enable dynamic configuration reloading (file watching).

        Returns:
            Self for method chaining

        Example:
            >>> builder.enable_dynamic_reloading()
        """
        self._dynamic_reloading = True
        return self

    def disable_dynamic_reloading(self) -> "ConfigBuilder":
        """Disable dynamic configuration reloading.

        Returns:
            Self for method chaining

        Example:
            >>> builder.disable_dynamic_reloading()
        """
        self._dynamic_reloading = False
        return self

    def enable_env_expander(self) -> "ConfigBuilder":
        """Enable environment variable expansion in config values.

        Returns:
            Self for method chaining

        Example:
            >>> builder.enable_env_expander()
        """
        self._use_env_expander = True
        return self

    def disable_env_expander(self) -> "ConfigBuilder":
        """Disable environment variable expansion.

        Returns:
            Self for method chaining

        Example:
            >>> builder.disable_env_expander()
        """
        self._use_env_expander = False
        return self

    def enable_type_casting(self) -> "ConfigBuilder":
        """Enable automatic type casting of config values.

        Returns:
            Self for method chaining

        Example:
            >>> builder.enable_type_casting()
        """
        self._use_type_casting = True
        return self

    def disable_type_casting(self) -> "ConfigBuilder":
        """Disable automatic type casting.

        Returns:
            Self for method chaining

        Example:
            >>> builder.disable_type_casting()
        """
        self._use_type_casting = False
        return self

    def enable_ide_support(self, stub_path: Optional[str] = None) -> "ConfigBuilder":
        """Enable IDE support (type stub generation).

        Args:
            stub_path: Optional custom path for IDE stub file

        Returns:
            Self for method chaining

        Example:
            >>> builder.enable_ide_support(".config_stash/stubs.pyi")
        """
        self._enable_ide_support = True
        self._ide_stub_path = stub_path
        return self

    def disable_ide_support(self) -> "ConfigBuilder":
        """Disable IDE support generation.

        Returns:
            Self for method chaining

        Example:
            >>> builder.disable_ide_support()
        """
        self._enable_ide_support = False
        return self

    def enable_debug(self) -> "ConfigBuilder":
        """Enable debug mode (detailed source tracking).

        Returns:
            Self for method chaining

        Example:
            >>> builder.enable_debug()
        """
        self._debug_mode = True
        return self

    def disable_debug(self) -> "ConfigBuilder":
        """Disable debug mode.

        Returns:
            Self for method chaining

        Example:
            >>> builder.disable_debug()
        """
        self._debug_mode = False
        return self

    def enable_deep_merge(self) -> "ConfigBuilder":
        """Enable deep merging of nested configurations.

        Returns:
            Self for method chaining

        Example:
            >>> builder.enable_deep_merge()
        """
        self._deep_merge = True
        return self

    def disable_deep_merge(self) -> "ConfigBuilder":
        """Disable deep merging (use shallow merge instead).

        Returns:
            Self for method chaining

        Example:
            >>> builder.disable_deep_merge()
        """
        self._deep_merge = False
        return self

    def with_schema(
        self, schema: Any, validate_on_load: bool = True, strict: bool = False
    ) -> "ConfigBuilder":
        """Configure schema validation for configuration.

        Args:
            schema: Pydantic model class or JSON Schema dictionary
            validate_on_load: If True, validate immediately after loading (default: True)
            strict: If True, raise ConfigValidationError on failure (default: False)

        Returns:
            Self for method chaining

        Example:
            >>> from pydantic import BaseModel
            >>> class AppConfig(BaseModel):
            ...     database_url: str
            >>> builder.with_schema(AppConfig, validate_on_load=True)
        """
        self._schema = schema
        self._validate_on_load = validate_on_load
        self._strict_validation = strict
        return self

    def enable_validation(self, strict: bool = False) -> "ConfigBuilder":
        """Enable validation using the configured schema.

        Args:
            strict: If True, raise ConfigValidationError on failure (default: False)

        Returns:
            Self for method chaining

        Example:
            >>> builder.enable_validation(strict=True)
        """
        self._validate_on_load = True
        self._strict_validation = strict
        return self

    def disable_validation(self) -> "ConfigBuilder":
        """Disable validation on load.

        Returns:
            Self for method chaining

        Example:
            >>> builder.disable_validation()
        """
        self._validate_on_load = False
        return self

    def build(self) -> "Config":
        """Build and return the Config instance.

        Returns:
            Configured Config instance

        Raises:
            ConfigStashError: If configuration is invalid

        Example:
            >>> config = builder.build()
        """
        # Use None for loaders if empty (allows default loading)
        loaders = self._loaders if self._loaders else None

        from config_stash.config import Config  # Import here to avoid circular import

        return Config(
            env=self._env,
            loaders=loaders,
            dynamic_reloading=self._dynamic_reloading,
            use_env_expander=self._use_env_expander,
            use_type_casting=self._use_type_casting,
            enable_ide_support=self._enable_ide_support,
            ide_stub_path=self._ide_stub_path,
            debug_mode=self._debug_mode,
            deep_merge=self._deep_merge,
            secret_resolver=self._secret_resolver,
            schema=self._schema,
            validate_on_load=self._validate_on_load,
            strict_validation=self._strict_validation,
        )

    @classmethod
    def create(cls) -> "ConfigBuilder":
        """Create a new ConfigBuilder instance.

        This is a convenience method for creating a builder. You can also
        use `ConfigBuilder()` directly.

        Returns:
            New ConfigBuilder instance

        Example:
            >>> builder = ConfigBuilder.create()
        """
        return cls()


# Convenience function for creating builders
def builder() -> ConfigBuilder:
    """Create a new ConfigBuilder instance.

    This is a convenience function for creating a builder with a shorter
    syntax: `builder().with_env("prod").build()`

    Returns:
        New ConfigBuilder instance

    Example:
        >>> from config_stash.config_builder import builder
        >>> config = builder().with_env("prod").build()
    """
    return ConfigBuilder()
