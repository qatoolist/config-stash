"""Async/await support for Config-Stash.

This module provides async versions of Config and loaders for use in
asynchronous Python applications.
"""

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence

from config_stash.config import Config
from config_stash.exceptions import ConfigLoadError

if TYPE_CHECKING:
    from config_stash.loaders.loader import Loader
    from config_stash.secret_stores.resolver import SecretResolver

logger = logging.getLogger(__name__)


class AsyncLoader:
    """Abstract base class for async configuration loaders.

    All async loaders must inherit from this class and implement
    the ``load()`` method as a coroutine.  Use async loaders when your
    configuration sources involve I/O that benefits from non-blocking
    execution (remote APIs, cloud storage, etc.).

    Example:
        >>> class AsyncRedisLoader(AsyncLoader):
        ...     async def load(self):
        ...         import aioredis
        ...         r = await aioredis.from_url(self.source)
        ...         return await r.hgetall("config")
    """

    def __init__(self, source: str) -> None:
        """Initialize the async loader.

        Args:
            source: The source identifier (file path, URL, prefix, etc.)
        """
        self.source: str = source
        self.config: Dict[str, Any] = {}

    async def load(self) -> Optional[Dict[str, Any]]:
        """Load configuration from the source (async).

        This method must be implemented by subclasses.

        Returns:
            Dictionary containing the loaded configuration, or None if the
            source doesn't exist or couldn't be loaded.

        Raises:
            ConfigLoadError: If loading fails due to an error
        """
        raise NotImplementedError("Async load method must be implemented by subclasses")


class AsyncYamlLoader(AsyncLoader):
    """Async YAML configuration loader.

    Reads a YAML file using a thread-pool executor so the event loop is
    never blocked by disk I/O.  Suitable for ``asyncio``-based applications
    that load configuration at startup.

    Example:
        >>> loader = AsyncYamlLoader("config.yaml")
        >>> config = await loader.load()
        >>> print(config["database"]["host"])
    """

    async def load(self) -> Optional[Dict[str, Any]]:
        """Load configuration from YAML file (async).

        Returns:
            Loaded configuration dictionary, or None if file doesn't exist

        Raises:
            ConfigLoadError: If loading fails
        """
        try:
            import yaml

            # Read file in thread pool to avoid blocking
            loop = asyncio.get_running_loop()
            content = await loop.run_in_executor(None, self._read_file_sync, self.source)
            self.config = yaml.safe_load(content)
            return self.config
        except FileNotFoundError:
            return None
        except Exception as e:
            raise ConfigLoadError(
                f"Failed to load YAML configuration from {self.source}",
                source=self.source,
                loader_type=self.__class__.__name__,
                original_error=e,
            ) from e

    def _read_file_sync(self, source: str) -> str:
        """Synchronous file read (executed in thread pool)."""
        with open(source, "r", encoding="utf-8") as f:
            return f.read()


class AsyncHTTPLoader(AsyncLoader):
    """Async HTTP configuration loader.

    Fetches configuration from a remote HTTP/HTTPS endpoint using
    ``aiohttp``.  The response format (JSON or YAML) is auto-detected
    from the ``Content-Type`` header or the URL file extension.

    Requires the ``aiohttp`` package (``pip install aiohttp``).

    Example:
        >>> loader = AsyncHTTPLoader("https://cfg.example.com/app.json", timeout=10)
        >>> config = await loader.load()
    """

    def __init__(self, url: str, timeout: int = 30) -> None:
        """Initialize async HTTP loader.

        Args:
            url: HTTP/HTTPS URL to load configuration from
            timeout: Request timeout in seconds
        """
        super().__init__(url)
        self.timeout = timeout

    async def load(self) -> Dict[str, Any]:
        """Load configuration from HTTP endpoint (async).

        Returns:
            Loaded configuration dictionary

        Raises:
            ConfigLoadError: If loading fails
        """
        try:
            import aiohttp  # type: ignore[import-untyped]
        except ImportError:
            raise ImportError(
                "aiohttp is required for async HTTP loading. Install with: pip install aiohttp"
            )

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as session:
                async with session.get(self.source) as response:
                    response.raise_for_status()
                    content = await response.text()

                    # Detect format from content-type or URL
                    content_type = response.headers.get("content-type", "")
                    if "json" in content_type or self.source.endswith(".json"):
                        import json

                        self.config = json.loads(content)
                    elif "yaml" in content_type or self.source.endswith((".yaml", ".yml")):
                        import yaml

                        self.config = yaml.safe_load(content)
                    else:
                        # Try JSON as default
                        import json

                        self.config = json.loads(content)

                    return self.config
        except Exception as e:
            raise ConfigLoadError(
                f"Failed to load HTTP configuration from {self.source}",
                source=self.source,
                loader_type=self.__class__.__name__,
                original_error=e,
            ) from e


class AsyncConfig:
    """Async version of Config for use in async applications.

    This class provides async methods for loading and managing configuration
    in asynchronous Python applications.

    Example:
        >>> async def main():
        ...     loader = AsyncYamlLoader("config.yaml")
        ...     config = await AsyncConfig.create(loaders=[loader])
        ...     value = await config.get_async("database.host")
    """

    def __init__(
        self,
        env: Optional[str] = None,
        loaders: Optional[Sequence[AsyncLoader]] = None,
        use_env_expander: bool = True,
        use_type_casting: bool = True,
        debug_mode: bool = False,
        deep_merge: bool = True,
        secret_resolver: Optional["SecretResolver"] = None,
    ) -> None:
        """Initialize AsyncConfig instance.

        Args:
            env: Environment name
            loaders: List of AsyncLoader instances
            use_env_expander: Enable environment variable expansion
            use_type_casting: Enable automatic type casting
            debug_mode: Enable debug mode
            deep_merge: Enable deep merging
            secret_resolver: Optional secret resolver
        """
        self.env = env or "development"
        self.use_env_expander = use_env_expander
        self.use_type_casting = use_type_casting
        self.debug_mode = debug_mode
        self.deep_merge = deep_merge
        self.secret_resolver = secret_resolver
        self._loaders = loaders or []
        self._config: Optional[Dict[str, Any]] = None
        self._merged_config: Optional[Dict[str, Any]] = None

    @classmethod
    async def create(
        cls,
        env: Optional[str] = None,
        loaders: Optional[Sequence[AsyncLoader]] = None,
        **kwargs: Any,
    ) -> "AsyncConfig":
        """Create and initialize AsyncConfig asynchronously.

        This is the preferred way to create an AsyncConfig instance
        as it properly handles async initialization.

        Args:
            env: Environment name
            loaders: List of AsyncLoader instances
            **kwargs: Additional arguments passed to __init__

        Returns:
            Initialized AsyncConfig instance

        Example:
            >>> config = await AsyncConfig.create(
            ...     env="production",
            ...     loaders=[AsyncYamlLoader("config.yaml")]
            ... )
        """
        instance = cls(env=env, loaders=loaders, **kwargs)
        await instance.load()
        return instance

    async def load(self) -> None:
        """Load configuration from all async loaders.

        This method must be called before accessing configuration values.

        Raises:
            ConfigLoadError: If loading fails
        """
        configs: List[Dict[str, Any]] = []

        # Load from all async loaders in parallel
        tasks = [loader.load() for loader in self._loaders]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        errors = []
        for result in results:
            if isinstance(result, BaseException):
                logger.warning(f"Failed to load configuration: {result}")
                if isinstance(result, Exception):
                    errors.append(result)
                continue
            if result is not None:
                configs.append(result)

        # If ALL loaders failed, raise instead of silently returning empty config
        if errors and not configs:
            raise ConfigLoadError(
                f"All {len(errors)} configuration loaders failed",
                source="async_loaders",
                original_error=errors[0],
            )

        # Merge configurations
        from config_stash.config_merger import ConfigMerger

        config_tuples = [(config, f"async_source_{i}") for i, config in enumerate(configs)]
        self._merged_config = ConfigMerger.merge_configs(config_tuples, deep_merge=self.deep_merge)
        self._config = self._merged_config

    async def get_async(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value asynchronously.

        Args:
            key_path: Dot-separated key path
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        if self._config is None:
            await self.load()

        from config_stash.config_introspection import get_nested_value

        return get_nested_value(self._config or {}, key_path, default)

    async def reload(self) -> None:
        """Reload configuration asynchronously.

        This method reloads all configurations from their sources.
        """
        self._config = None
        self._merged_config = None
        await self.load()

    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary.

        Returns:
            Configuration dictionary
        """
        return self._config or {}

    async def validate_async(self, schema: Optional[Any] = None) -> bool:
        """Validate configuration asynchronously.

        Args:
            schema: Optional schema to validate against

        Returns:
            True if valid, False otherwise
        """
        if self._config is None:
            await self.load()

        # Validation is typically CPU-bound, so run in executor
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._validate_sync, self._config or {}, schema)

    def _validate_sync(self, config: Dict[str, Any], schema: Any) -> bool:
        """Synchronous validation (run in executor)."""
        if not schema:
            return bool(config)

        # Use Pydantic validation if schema is a Pydantic model
        is_pydantic = False
        try:
            from pydantic import BaseModel
            is_pydantic = isinstance(schema, type) and issubclass(schema, BaseModel)
        except ImportError:
            pass
        if is_pydantic:
            from config_stash.validators.pydantic_validator import PydanticValidator

            validator = PydanticValidator(schema)
            try:
                validator.validate(config)
                return True
            except Exception:
                return False

        return bool(config)
