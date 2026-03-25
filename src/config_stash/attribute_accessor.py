from typing import Any, Optional

from config_stash.exceptions import ConfigNotFoundError
from config_stash.hook_processor import HookProcessor
from config_stash.utils.lazy_loader import LazyLoader


class AttributeAccessor:
    """Provides attribute-style access to configuration values.

    This class enables dot-notation access to configuration values
    (e.g., `config.database.host`) while applying registered hooks
    and providing lazy loading of nested configurations.
    """

    def __init__(
        self, lazy_loader: LazyLoader, hook_processor: Optional[HookProcessor] = None
    ) -> None:
        """Initialize the attribute accessor.

        Args:
            lazy_loader: LazyLoader instance for accessing configuration values
            hook_processor: Optional HookProcessor for transforming values
        """
        self.lazy_loader: LazyLoader = lazy_loader
        self.hook_processor: Optional[HookProcessor] = hook_processor

    def __getattr__(self, item: str) -> Any:
        """Get configuration value using attribute-style access.

        Args:
            item: Configuration key to retrieve

        Returns:
            Configuration value after processing through hooks

        Raises:
            AttributeError: If the configuration key doesn't exist

        Example:
            >>> accessor = AttributeAccessor(lazy_loader)
            >>> value = accessor.database.host  # Instead of config['database']['host']
        """
        try:
            value = self.lazy_loader.get(item)
            if isinstance(value, dict):
                # Create nested AttributeAccessor for nested configurations
                nested_loader = LazyLoader(value)
                return AttributeAccessor(nested_loader, self.hook_processor)
            # Apply hooks if hook_processor is available
            if self.hook_processor:
                value = self.hook_processor.process_hooks(item, value)
            return value
        except KeyError as e:
            raise AttributeError(
                f"'Config' object has no attribute '{item}'"
            ) from ConfigNotFoundError(
                f"Configuration key '{item}' not found",
                key=item,
            )
