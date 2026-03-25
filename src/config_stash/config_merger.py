from typing import Any, Dict, List, Tuple

from config_stash.exceptions import ConfigMergeConflictError


class ConfigMerger:
    """Utility class for merging configuration dictionaries.

    Provides static methods for merging configurations from multiple sources,
    supporting both shallow and deep merge strategies.
    """

    @staticmethod
    def merge_configs(
        configs: List[Tuple[Dict[str, Any], str]], deep_merge: bool = False
    ) -> Dict[str, Any]:
        """Merge multiple configurations into a single dictionary.

        Configurations are merged in order, with later configurations
        taking precedence over earlier ones (for shallow merge) or
        being deeply merged (for deep merge).

        Args:
            configs: List of (configuration_dict, source) tuples to merge
            deep_merge: If True, perform deep merge of nested dictionaries.
                       If False, later configs completely replace earlier values.

        Returns:
            Merged configuration dictionary

        Example:
            >>> configs = [
            ...     ({"a": 1, "b": {"c": 2}}, "source1"),
            ...     ({"b": {"d": 3}}, "source2"),
            ... ]
            >>> result = ConfigMerger.merge_configs(configs, deep_merge=True)
            >>> # Result: {"a": 1, "b": {"c": 2, "d": 3}}
        """
        merged_config: Dict[str, Any] = {}
        for config, source in configs:
            try:
                merged_config = ConfigMerger._merge_dicts(merged_config, config, deep_merge, source)
            except Exception as e:
                raise ConfigMergeConflictError(
                    f"Failed to merge configuration from {source}: {e}",
                    key="",
                    new_source=source,
                ) from e
        return merged_config

    @staticmethod
    def _merge_dicts(
        base: Dict[str, Any],
        new: Dict[str, Any],
        deep_merge: bool,
        source: str = "",
    ) -> Dict[str, Any]:
        """Merge two configuration dictionaries.

        Args:
            base: Base configuration dictionary (not modified)
            new: New configuration dictionary to merge in
            deep_merge: If True, recursively merge nested dictionaries
            source: Source identifier for error messages (optional)

        Returns:
            New merged configuration dictionary

        Raises:
            ConfigMergeConflictError: If merge fails due to incompatible types
        """
        if deep_merge:
            from config_stash.utils.dict_utils import deep_merge_dicts

            return deep_merge_dicts(base, new)
        else:
            import copy

            result = copy.copy(base)
            result.update(new)
            return result
