"""Automatic type casting hook for configuration values.

This module provides the ``TypeCasting`` class, which converts string
configuration values into their natural Python types (``int``, ``float``,
``bool``, ``None``) using heuristic parsing.  This is particularly useful when
configuration originates from sources that represent all values as strings,
such as environment variables or ``.env`` files.

Register the hook with the config-stash hook processor so that string values
like ``"42"``, ``"3.14"``, ``"true"``, and ``"null"`` are automatically
converted to ``int``, ``float``, ``bool``, and ``None`` respectively.

Example:
    >>> TypeCasting.cast("42")
    42
    >>> TypeCasting.cast("true")
    True
    >>> TypeCasting.cast("hello")
    'hello'
"""

from config_stash.utils.type_coercion import parse_scalar_value


class TypeCasting:
    """Casts string configuration values to native Python scalar types.

    ``TypeCasting`` inspects each string value and attempts to parse it as an
    ``int``, ``float``, ``bool``, or ``None``.  Strings that do not match any
    known pattern are returned unchanged.  Non-string values pass through
    without modification.

    Example:
        >>> TypeCasting.cast("3.14")
        3.14
        >>> TypeCasting.cast("false")
        False
        >>> TypeCasting.cast([1, 2, 3])
        [1, 2, 3]
    """

    @staticmethod
    def cast(value):
        """Attempt to convert a string value to its native Python type.

        Delegates to ``parse_scalar_value`` for the actual parsing logic.
        Non-string values are returned as-is.

        Args:
            value: The value to cast.  Only ``str`` instances are processed;
                all other types pass through unmodified.

        Returns:
            The parsed Python object if the string matches a known scalar
            pattern (integer, float, boolean, or null), or the original
            string if no conversion applies.  Non-string inputs are returned
            unchanged.

        Example:
            >>> TypeCasting.cast("100")
            100
            >>> TypeCasting.cast("null")  # or "None", depending on coercion rules
            >>> TypeCasting.cast({"key": "val"})
            {'key': 'val'}
        """
        if isinstance(value, str):
            return parse_scalar_value(value)
        return value

    @staticmethod
    def hook(value):
        """Hook entry point for the config-stash hook processor.

        This method serves as the standard hook interface expected by the
        hook processor.  It delegates directly to ``cast()``.

        Args:
            value: The configuration value to process.

        Returns:
            The value after type casting.

        Example:
            >>> # Register with hook processor
            >>> hook_processor.register(TypeCasting.hook)
        """
        return TypeCasting.cast(value)
