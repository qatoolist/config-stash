"""Advanced merging strategies for Config-Stash.

This module provides different merge strategies for combining configurations,
allowing fine-grained control over how values are merged.
"""

import logging
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class MergeStrategy(Enum):
    """Merge strategies for configuration values.

    This enum defines the available strategies for merging configuration
    values when combining configurations from multiple sources.

    Attributes:
        REPLACE: Replace the base value entirely with the new value.
            Use this when you want new values to completely override existing ones.
        MERGE: Deep merge nested dictionaries while preserving existing values.
            Use this for nested configurations where you want to combine values.
        APPEND: Append new list items to the end of existing lists.
            Use this when you want to combine list values.
        PREPEND: Prepend new list items to the beginning of existing lists.
            Use this when new list items should have priority.
        INTERSECTION: Keep only keys that exist in both configurations.
            Use this to create a configuration with only common settings.
        UNION: Keep all keys from both configurations, merging values for common keys.
            Use this to combine all available configuration options.

    Example:
        >>> from config_stash.merge_strategies import MergeStrategy, AdvancedConfigMerger
        >>> merger = AdvancedConfigMerger(MergeStrategy.MERGE)
        >>> merger.set_strategy("database", MergeStrategy.REPLACE)
        >>> result = merger.merge(base_config, override_config)
    """

    REPLACE = "replace"  # Replace base value with new value
    MERGE = "merge"  # Deep merge nested dictionaries
    APPEND = "append"  # Append to lists
    PREPEND = "prepend"  # Prepend to lists
    INTERSECTION = "intersection"  # Keep only common keys
    UNION = "union"  # Keep all keys from both configs


class AdvancedConfigMerger:
    """Advanced configuration merger with strategy support.

    This class provides configurable merge strategies for combining
    configurations with fine-grained control over merge behavior.
    """

    def __init__(self, default_strategy: MergeStrategy = MergeStrategy.MERGE) -> None:
        """Initialize the advanced config merger.

        Args:
            default_strategy: Default merge strategy to use
        """
        self.default_strategy = default_strategy
        self.strategy_map: Dict[str, MergeStrategy] = {}

    def set_strategy(self, key_path: str, strategy: MergeStrategy) -> None:
        """Set merge strategy for a specific key path.

        Args:
            key_path: Dot-separated key path (e.g., "database", "app.debug")
            strategy: Merge strategy to use for this key

        Example:
            >>> merger = AdvancedConfigMerger()
            >>> merger.set_strategy("database", MergeStrategy.REPLACE)
            >>> merger.set_strategy("app.debug", MergeStrategy.REPLACE)
        """
        self.strategy_map[key_path] = strategy

    def merge(
        self,
        base: Dict[str, Any],
        new: Dict[str, Any],
        path: str = "",
    ) -> Dict[str, Any]:
        """Merge two configurations using configured strategies.

        Args:
            base: Base configuration dictionary
            new: New configuration dictionary to merge in
            path: Current path prefix (for strategy lookup)

        Returns:
            Merged configuration dictionary

        Example:
            >>> merger = AdvancedConfigMerger()
            >>> base = {"database": {"host": "localhost"}, "app": {"debug": True}}
            >>> new = {"database": {"port": 5432}}
            >>> result = merger.merge(base, new)
            >>> # Result: {"database": {"host": "localhost", "port": 5432}, "app": {"debug": True}}
        """
        # Handle INTERSECTION strategy at top level - only keep common keys
        if self.default_strategy == MergeStrategy.INTERSECTION:
            if isinstance(base, dict) and isinstance(new, dict):
                result = {}
                common_keys = set(base.keys()) & set(new.keys())
                for key in common_keys:
                    full_path = f"{path}.{key}" if path else key
                    strategy = self._get_strategy(full_path)
                    result[key] = self._apply_strategy(
                        base[key], new[key], strategy, full_path
                    )
                return result
            # For non-dicts, return intersection logic
            return new if base == new else {}

        result = base.copy()

        for key, value in new.items():
            full_path = f"{path}.{key}" if path else key
            strategy = self._get_strategy(full_path)

            if key in result:
                result[key] = self._apply_strategy(
                    result[key], value, strategy, full_path
                )
            else:
                result[key] = value

        return result

    def _get_strategy(self, path: str) -> MergeStrategy:
        """Get merge strategy for a key path.

        Checks for exact match first, then checks parent paths.

        Args:
            path: Dot-separated key path

        Returns:
            Merge strategy to use
        """
        # Check for exact match
        if path in self.strategy_map:
            return self.strategy_map[path]

        # Check parent paths (most specific match)
        parts = path.split(".")
        for i in range(len(parts) - 1, 0, -1):
            parent_path = ".".join(parts[:i])
            if parent_path in self.strategy_map:
                return self.strategy_map[parent_path]

        return self.default_strategy

    def _apply_strategy(
        self,
        base_value: Any,
        new_value: Any,
        strategy: MergeStrategy,
        path: str,
    ) -> Any:
        """Apply merge strategy to two values.

        This is an internal method that applies the specified merge strategy
        to combine base_value and new_value. The strategy determines how the
        values are merged (replace, deep merge, append, etc.).

        Args:
            base_value: Base value from the existing configuration
            new_value: New value from the configuration being merged in
            strategy: Merge strategy to apply (from MergeStrategy enum)
            path: Full dot-separated key path (for nested strategy lookup and logging)

        Returns:
            Merged value according to the specified strategy

        Note:
            - For REPLACE: Returns new_value
            - For MERGE: Recursively merges dictionaries
            - For APPEND/PREPEND: Combines lists
            - For INTERSECTION/UNION: Applies set operations on dictionary keys
        """
        if strategy == MergeStrategy.REPLACE:
            return new_value

        elif strategy == MergeStrategy.MERGE:
            if isinstance(base_value, dict) and isinstance(new_value, dict):
                return self.merge(base_value, new_value, path)
            else:
                # Type mismatch - replace
                return new_value

        elif strategy == MergeStrategy.APPEND:
            if isinstance(base_value, list) and isinstance(new_value, list):
                return base_value + new_value
            elif isinstance(base_value, list):
                return base_value + [new_value]
            else:
                # Not a list - convert and append
                return [base_value, new_value]

        elif strategy == MergeStrategy.PREPEND:
            if isinstance(base_value, list) and isinstance(new_value, list):
                return new_value + base_value
            elif isinstance(base_value, list):
                return [new_value] + base_value
            else:
                # Not a list - convert and prepend
                return [new_value, base_value]

        elif strategy == MergeStrategy.INTERSECTION:
            if isinstance(base_value, dict) and isinstance(new_value, dict):
                result = {}
                common_keys = set(base_value.keys()) & set(new_value.keys())
                for key in common_keys:
                    full_path = f"{path}.{key}"
                    result[key] = self._apply_strategy(
                        base_value[key],
                        new_value[key],
                        self._get_strategy(full_path),
                        full_path,
                    )
                return result
            else:
                # Not dicts - use base if values match, otherwise replace
                return new_value if base_value == new_value else base_value

        elif strategy == MergeStrategy.UNION:
            if isinstance(base_value, dict) and isinstance(new_value, dict):
                # Union all keys
                result = base_value.copy()
                for key, val in new_value.items():
                    if key in result:
                        full_path = f"{path}.{key}"
                        result[key] = self._apply_strategy(
                            result[key], val, self._get_strategy(full_path), full_path
                        )
                    else:
                        result[key] = val
                return result
            else:
                # Not dicts - use new value
                return new_value

        else:
            # Default: replace
            return new_value
