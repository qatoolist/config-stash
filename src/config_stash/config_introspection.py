"""Configuration introspection utilities for Config-Stash.

This module provides utilities for querying and inspecting configuration
structure, types, and values.
"""

from typing import Any, Dict, List, Optional, Set


def get_all_keys(config: Dict[str, Any], prefix: str = "") -> List[str]:
    """Recursively get all keys from a configuration dictionary.

    Args:
        config: Configuration dictionary
        prefix: Optional prefix for nested keys (e.g., "database" for nested keys)

    Returns:
        List of dot-separated key paths

    Example:
        >>> config = {"database": {"host": "localhost", "port": 5432}}
        >>> get_all_keys(config)
        ['database', 'database.host', 'database.port']
    """
    keys: List[str] = []
    for key, value in config.items():
        full_key = f"{prefix}.{key}" if prefix else key
        keys.append(full_key)
        if isinstance(value, dict):
            keys.extend(get_all_keys(value, full_key))
    return keys


def get_nested_value(config: Dict[str, Any], key_path: str, default: Any = None) -> Any:
    """Get a nested value from configuration using dot notation.

    Args:
        config: Configuration dictionary
        key_path: Dot-separated key path (e.g., "database.host")
        default: Default value if key not found

    Returns:
        Configuration value or default if not found

    Example:
        >>> config = {"database": {"host": "localhost"}}
        >>> get_nested_value(config, "database.host")
        'localhost'
        >>> get_nested_value(config, "database.port", default=5432)
        5432
    """
    keys = key_path.split(".")
    current = config
    try:
        for key in keys:
            if isinstance(current, dict):
                current = current[key]
            else:
                return default
        return current
    except (KeyError, TypeError):
        return default


def has_key(config: Dict[str, Any], key_path: str) -> bool:
    """Check if a configuration key exists.

    Args:
        config: Configuration dictionary
        key_path: Dot-separated key path (e.g., "database.host")

    Returns:
        True if key exists, False otherwise

    Example:
        >>> config = {"database": {"host": "localhost"}}
        >>> has_key(config, "database.host")
        True
        >>> has_key(config, "database.port")
        False
    """
    keys = key_path.split(".")
    current = config
    try:
        for key in keys:
            if isinstance(current, dict):
                current = current[key]
            else:
                return False
        return True
    except (KeyError, TypeError):
        return False


def infer_type(value: Any) -> str:
    """Infer the type name of a configuration value.

    Args:
        value: Configuration value

    Returns:
        Type name as string (e.g., "str", "int", "dict", "list")

    Example:
        >>> infer_type("hello")
        'str'
        >>> infer_type(42)
        'int'
        >>> infer_type({"key": "value"})
        'dict'
    """
    type_name = type(value).__name__
    # Map some common types to more descriptive names
    type_map = {
        "str": "str",
        "int": "int",
        "float": "float",
        "bool": "bool",
        "list": "list",
        "dict": "dict",
        "NoneType": "None",
    }
    return type_map.get(type_name, type_name)


def get_schema_info(config: Dict[str, Any], key_path: str = "") -> Dict[str, Any]:
    """Get schema information for a configuration key or entire config.

    Args:
        config: Configuration dictionary
        key_path: Optional dot-separated key path. If empty, returns schema for entire config.

    Returns:
        Dictionary with schema information (type, required, nested keys, etc.)

    Example:
        >>> config = {"database": {"host": "localhost", "port": 5432}}
        >>> schema = get_schema_info(config, "database")
        >>> schema["type"]  # 'dict'
        >>> schema["keys"]  # ['host', 'port']
    """
    if key_path:
        keys = key_path.split(".")
        current = config
        try:
            for key in keys:
                if isinstance(current, dict):
                    current = current[key]
                else:
                    return {"type": "unknown", "exists": False}
        except (KeyError, TypeError):
            return {"type": "unknown", "exists": False}
        value = current
    else:
        value = config

    schema: Dict[str, Any] = {
        "type": infer_type(value),
        "exists": True,
    }

    if isinstance(value, dict):
        schema["keys"] = list(value.keys())
        schema["nested"] = {k: infer_type(v) for k, v in value.items()}
    elif isinstance(value, list):
        schema["length"] = len(value)
        if value:
            schema["item_type"] = infer_type(value[0])

    return schema
