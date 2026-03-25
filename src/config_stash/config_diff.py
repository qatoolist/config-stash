"""Advanced configuration diff and drift detection for Config-Stash.

This module provides comprehensive diff functionality and drift detection
to compare configurations and detect discrepancies.
"""

import json
import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class DiffType(Enum):
    """Types of configuration differences."""

    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


class ConfigDiff:
    """Represents a difference between two configurations.

    This class encapsulates a single difference between two configuration
    dictionaries, including the key, type of change, and both old and new values.

    Attributes:
        key: The configuration key that differs (e.g., "host")
        diff_type: Type of difference (ADDED, REMOVED, MODIFIED, UNCHANGED)
        old_value: Original value in the first configuration
        new_value: New value in the second configuration
        path: Full dot-separated path to the key (e.g., "database.host")
        nested_diffs: List of nested ConfigDiff objects for complex nested changes

    Example:
        >>> diff = ConfigDiff(
        ...     key="host",
        ...     diff_type=DiffType.MODIFIED,
        ...     old_value="localhost",
        ...     new_value="remote",
        ...     path="database.host"
        ... )
        >>> print(f"{diff.path}: {diff.diff_type.value}")
        database.host: modified
    """

    def __init__(
        self,
        key: str,
        diff_type: DiffType,
        old_value: Any = None,
        new_value: Any = None,
        path: str = "",
    ) -> None:
        """Initialize a configuration diff.

        Args:
            key: Configuration key that differs
            diff_type: Type of difference (ADDED, REMOVED, MODIFIED, UNCHANGED)
            old_value: Original value in the first configuration
            new_value: New value in the second configuration
            path: Full dot-separated path to the key (for nested configurations)
        """
        self.key = key
        self.diff_type = diff_type
        self.old_value = old_value
        self.new_value = new_value
        self.path = path
        self.nested_diffs: List["ConfigDiff"] = []

    def __repr__(self) -> str:
        """String representation of the diff."""
        return (
            f"ConfigDiff(key={self.key}, type={self.diff_type.value}, "
            f"path={self.path})"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert diff to dictionary representation.

        Returns:
            Dictionary representation of the diff
        """
        result: Dict[str, Any] = {
            "key": self.key,
            "path": self.path,
            "type": self.diff_type.value,
        }
        if self.diff_type in (DiffType.MODIFIED, DiffType.REMOVED):
            result["old_value"] = self.old_value
        if self.diff_type in (DiffType.MODIFIED, DiffType.ADDED):
            result["new_value"] = self.new_value
        if self.nested_diffs:
            result["nested"] = [d.to_dict() for d in self.nested_diffs]
        return result


class ConfigDiffer:
    """Advanced configuration differ with structured diff output.

    This class provides utilities for comparing two configurations and
    generating structured diff results. It supports nested configurations
    and provides detailed information about all differences.

    Example:
        >>> config1 = {"database": {"host": "localhost", "port": 5432}}
        >>> config2 = {"database": {"host": "remote", "port": 5432, "ssl": True}}
        >>> diffs = ConfigDiffer.diff(config1, config2)
        >>> summary = ConfigDiffer.diff_summary(diffs)
        >>> print(f"Found {summary['total']} differences")
    """

    @staticmethod
    def diff(
        config1: Dict[str, Any],
        config2: Dict[str, Any],
        path: str = "",
    ) -> List[ConfigDiff]:
        """Generate structured diff between two configurations.

        Args:
            config1: First configuration dictionary
            config2: Second configuration dictionary
            path: Current path prefix (for nested keys)

        Returns:
            List of ConfigDiff objects representing all differences

        Example:
            >>> config1 = {"database": {"host": "localhost"}}
            >>> config2 = {"database": {"host": "remote"}}
            >>> diffs = ConfigDiffer.diff(config1, config2)
            >>> diffs[0].key  # 'host'
            >>> diffs[0].diff_type  # DiffType.MODIFIED
        """
        diffs: List[ConfigDiff] = []
        all_keys: Set[str] = set(config1.keys()) | set(config2.keys())

        for key in sorted(all_keys):
            full_path = f"{path}.{key}" if path else key
            val1 = config1.get(key)
            val2 = config2.get(key)

            if key not in config1:
                # Key added in config2
                diffs.append(
                    ConfigDiff(
                        key=key,
                        diff_type=DiffType.ADDED,
                        new_value=val2,
                        path=full_path,
                    )
                )
            elif key not in config2:
                # Key removed in config2
                diffs.append(
                    ConfigDiff(
                        key=key,
                        diff_type=DiffType.REMOVED,
                        old_value=val1,
                        path=full_path,
                    )
                )
            elif isinstance(val1, dict) and isinstance(val2, dict):
                # Both are dicts - recurse
                nested_diffs = ConfigDiffer.diff(val1, val2, full_path)
                if nested_diffs:
                    diff = ConfigDiff(
                        key=key, diff_type=DiffType.MODIFIED, path=full_path
                    )
                    diff.nested_diffs = nested_diffs
                    diffs.append(diff)
            elif val1 != val2:
                # Values differ
                diffs.append(
                    ConfigDiff(
                        key=key,
                        diff_type=DiffType.MODIFIED,
                        old_value=val1,
                        new_value=val2,
                        path=full_path,
                    )
                )

        return diffs

    @staticmethod
    def diff_summary(diffs: List[ConfigDiff]) -> Dict[str, Any]:
        """Generate summary of differences.

        Args:
            diffs: List of ConfigDiff objects

        Returns:
            Dictionary with summary statistics
        """
        summary = {
            "total": 0,
            "added": 0,
            "removed": 0,
            "modified": 0,
        }

        def count_diffs(diff_list: List[ConfigDiff]) -> None:
            for diff in diff_list:
                summary["total"] += 1
                summary[diff.diff_type.value] = summary.get(diff.diff_type.value, 0) + 1
                if diff.nested_diffs:
                    count_diffs(diff.nested_diffs)

        count_diffs(diffs)
        return summary

    @staticmethod
    def diff_to_json(diffs: List[ConfigDiff], indent: int = 2) -> str:
        """Convert diff list to JSON string.

        Args:
            diffs: List of ConfigDiff objects
            indent: JSON indentation level

        Returns:
            JSON string representation
        """
        return json.dumps([d.to_dict() for d in diffs], indent=indent, default=str)


class ConfigDriftDetector:
    """Detects configuration drift (intended vs. actual state).

    Configuration drift occurs when the actual configuration differs from
    the intended or target configuration. This class helps identify such
    discrepancies, which is useful for compliance, auditing, and troubleshooting.

    Attributes:
        intended_config: The intended/target configuration state

    Example:
        >>> intended = {"database": {"host": "prod-db.example.com"}}
        >>> actual = {"database": {"host": "dev-db.example.com"}}
        >>> detector = ConfigDriftDetector(intended)
        >>> drift = detector.detect_drift(actual)
        >>> if drift:
        ...     print(f"Configuration drift detected: {len(drift)} differences")
        ...     for diff in drift:
        ...         print(f"  {diff.path}: expected {diff.old_value}, got {diff.new_value}")

    See Also:
        ConfigDiffer: For comparing two arbitrary configurations
    """

    def __init__(self, intended_config: Dict[str, Any]) -> None:
        """Initialize drift detector.

        Args:
            intended_config: The intended/target configuration state
        """
        self.intended_config = intended_config

    def detect_drift(self, actual_config: Dict[str, Any]) -> List[ConfigDiff]:
        """Detect drift between intended and actual configuration.

        Args:
            actual_config: The actual current configuration

        Returns:
            List of ConfigDiff objects representing drift

        Example:
            >>> detector = ConfigDriftDetector(intended_config)
            >>> drift = detector.detect_drift(actual_config)
            >>> if drift:
            ...     print(f"Configuration drift detected: {len(drift)} differences")
        """
        return ConfigDiffer.diff(self.intended_config, actual_config)

    def has_drift(self, actual_config: Dict[str, Any]) -> bool:
        """Check if drift exists without generating full diff.

        Args:
            actual_config: The actual current configuration

        Returns:
            True if drift detected, False otherwise
        """
        return len(self.detect_drift(actual_config)) > 0
