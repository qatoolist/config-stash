"""Shared type coercion utility for parsing scalar string values."""

from typing import Any, Union


def parse_scalar_value(
    value: str,
    extended_booleans: bool = False,
) -> Union[bool, int, float, str]:
    """Parse a string value into its most appropriate Python type.

    Checks boolean first, then int, then float, then returns string.

    Args:
        value: String value to parse
        extended_booleans: If True, also accept "yes"/"no"/"on"/"off" as booleans

    Returns:
        Parsed value as bool, int, float, or str

    Example:
        >>> parse_scalar_value("42")
        42
        >>> parse_scalar_value("3.14")
        3.14
        >>> parse_scalar_value("true")
        True
        >>> parse_scalar_value("yes", extended_booleans=True)
        True
        >>> parse_scalar_value("hello")
        'hello'
    """
    lower = value.lower()

    # Boolean detection
    true_values = {"true"}
    false_values = {"false"}
    if extended_booleans:
        true_values.update({"yes", "on"})
        false_values.update({"no", "off"})

    if lower in true_values:
        return True
    if lower in false_values:
        return False

    # Integer detection (handles negatives)
    try:
        return int(value)
    except ValueError:
        pass

    # Float detection
    try:
        return float(value)
    except ValueError:
        pass

    return value
