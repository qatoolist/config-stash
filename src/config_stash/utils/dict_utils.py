"""Shared dictionary utilities for merging and nested key access."""

import copy
from typing import Any, Dict, Optional, Set


def deep_merge_dicts(
    base: Dict[str, Any],
    new: Dict[str, Any],
    skip_keys: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """Deep merge two dictionaries without mutating either input.

    Args:
        base: Base dictionary (not modified)
        new: Dictionary to merge in (values take precedence)
        skip_keys: Optional set of keys to skip during merge

    Returns:
        New merged dictionary

    Example:
        >>> base = {"database": {"host": "localhost", "port": 5432}}
        >>> overrides = {"database": {"host": "db.prod"}, "debug": True}
        >>> deep_merge_dicts(base, overrides)
        {'database': {'host': 'db.prod', 'port': 5432}, 'debug': True}
    """
    result = copy.copy(base)
    for key, value in new.items():
        if skip_keys and key in skip_keys:
            continue
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            result[key] = deep_merge_dicts(result[key], value, skip_keys)
        else:
            result[key] = value
    return result


def get_nested(d: Dict[str, Any], key_path: str, default: Any = None) -> Any:
    """Get a value from a nested dictionary using a dot-separated key path.

    Args:
        d: Dictionary to traverse
        key_path: Dot-separated key path (e.g., "database.host")
        default: Value to return if key not found

    Returns:
        Value at the key path, or default if not found

    Example:
        >>> d = {"database": {"host": "localhost", "port": 5432}}
        >>> get_nested(d, "database.host")
        'localhost'
        >>> get_nested(d, "database.timeout", default=30)
        30
    """
    if not key_path:
        return d

    current = d
    for key in key_path.split("."):
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


def set_nested(d: Dict[str, Any], key_path: str, value: Any) -> None:
    """Set a value in a nested dictionary using a dot-separated key path.

    Creates intermediate dictionaries as needed. If a non-dict value
    exists at an intermediate key, it is replaced with a dict.

    Args:
        d: Dictionary to modify (mutated in-place)
        key_path: Dot-separated key path (e.g., "database.host")
        value: Value to set

    Example:
        >>> d = {}
        >>> set_nested(d, "database.host", "localhost")
        >>> d
        {'database': {'host': 'localhost'}}
    """
    keys = key_path.split(".")
    current = d
    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value
