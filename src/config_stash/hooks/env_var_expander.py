"""Environment variable expansion hook for configuration values.

This module provides the ``EnvVarExpander`` class, which replaces
``${VAR_NAME}`` placeholders inside string configuration values with the
corresponding environment variable values at load time.  Placeholders whose
environment variables are not set are left unchanged.

Register the hook with the config-stash hook processor so that every string
value is automatically expanded before it reaches the application.

Example:
    >>> import os
    >>> os.environ["DB_HOST"] = "prod-db.example.com"
    >>> EnvVarExpander.expand("jdbc:mysql://${DB_HOST}:3306/mydb")
    'jdbc:mysql://prod-db.example.com:3306/mydb'
"""

import os
import re


class EnvVarExpander:
    """Expands ``${VAR}`` placeholders in strings using environment variables.

    The class uses a pre-compiled regular expression to find all occurrences
    of the ``${...}`` pattern and replaces each one with the value of the
    named environment variable.  If the variable is not set, the original
    placeholder text is preserved verbatim.

    Attributes:
        env_var_pattern: A compiled regular expression matching ``${VAR_NAME}``
            tokens.  Nested braces are not supported.

    Example:
        >>> import os
        >>> os.environ["APP_PORT"] = "8080"
        >>> EnvVarExpander.expand("http://localhost:${APP_PORT}/api")
        'http://localhost:8080/api'
    """

    env_var_pattern = re.compile(r"\$\{([^}^{]+)\}")

    @staticmethod
    def expand(value):
        """Replace ``${VAR}`` placeholders in a string with environment variable values.

        Non-string values are returned as-is without modification.  If a
        placeholder references an environment variable that is not set, the
        placeholder is left in the string unchanged.

        Args:
            value: The value to process.  Only ``str`` instances are expanded;
                all other types pass through unmodified.

        Returns:
            The expanded string with environment variable values substituted,
            or the original ``value`` if it is not a string.

        Example:
            >>> import os
            >>> os.environ["HOME_DIR"] = "/home/user"
            >>> EnvVarExpander.expand("${HOME_DIR}/config.yaml")
            '/home/user/config.yaml'
            >>> EnvVarExpander.expand(42)
            42
        """
        if isinstance(value, str):
            return EnvVarExpander.env_var_pattern.sub(
                lambda match: os.environ.get(match.group(1), match.group(0)), value
            )
        return value

    @staticmethod
    def hook(value):
        """Hook entry point for the config-stash hook processor.

        This method serves as the standard hook interface expected by the
        hook processor.  It delegates directly to ``expand()``.

        Args:
            value: The configuration value to process.

        Returns:
            The value after environment variable expansion.

        Example:
            >>> # Register with hook processor
            >>> hook_processor.register(EnvVarExpander.hook)
        """
        return EnvVarExpander.expand(value)
