"""TOML compatibility layer.

Uses stdlib tomllib (Python 3.11+) or tomli as fallback.
Falls back to the deprecated toml package as a last resort.

This module exposes three public functions -- ``loads``, ``load_file``,
and ``dumps`` -- that provide a unified TOML API regardless of which
underlying library is available.
"""

import sys
from typing import Any, Dict

# Try stdlib first (Python 3.11+), then tomli, then legacy toml
if sys.version_info >= (3, 11):
    import tomllib

    def loads(s: str) -> Dict[str, Any]:
        """Parse a TOML-formatted string into a dictionary.

        Uses the stdlib ``tomllib`` module (Python 3.11+).

        Args:
            s: A string containing valid TOML.

        Returns:
            Parsed configuration as a dictionary.

        Raises:
            tomllib.TOMLDecodeError: If the string is not valid TOML.

        Example:
            >>> from config_stash.utils.toml_compat import loads
            >>> config = loads('[database]\\nhost = "localhost"')
            >>> print(config["database"]["host"])
            localhost
        """
        return tomllib.loads(s)

    def load_file(path: str) -> Dict[str, Any]:
        """Load and parse a TOML file into a dictionary.

        Uses the stdlib ``tomllib`` module (Python 3.11+).

        Args:
            path: Path to a TOML file.

        Returns:
            Parsed configuration as a dictionary.

        Raises:
            FileNotFoundError: If the file does not exist.
            tomllib.TOMLDecodeError: If the file is not valid TOML.

        Example:
            >>> from config_stash.utils.toml_compat import load_file
            >>> config = load_file("pyproject.toml")
        """
        with open(path, "rb") as f:
            return tomllib.load(f)

    TomlDecodeError = tomllib.TOMLDecodeError

else:
    try:
        import tomli

        def loads(s: str) -> Dict[str, Any]:
            """Parse a TOML-formatted string into a dictionary.

            Uses the ``tomli`` third-party library.

            Args:
                s: A string containing valid TOML.

            Returns:
                Parsed configuration as a dictionary.

            Raises:
                tomli.TOMLDecodeError: If the string is not valid TOML.

            Example:
                >>> from config_stash.utils.toml_compat import loads
                >>> config = loads('[server]\\nport = 8080')
            """
            return tomli.loads(s)

        def load_file(path: str) -> Dict[str, Any]:
            """Load and parse a TOML file into a dictionary.

            Uses the ``tomli`` third-party library.

            Args:
                path: Path to a TOML file.

            Returns:
                Parsed configuration as a dictionary.

            Raises:
                FileNotFoundError: If the file does not exist.
                tomli.TOMLDecodeError: If the file is not valid TOML.

            Example:
                >>> from config_stash.utils.toml_compat import load_file
                >>> config = load_file("pyproject.toml")
            """
            with open(path, "rb") as f:
                return tomli.load(f)

        TomlDecodeError = tomli.TOMLDecodeError

    except ImportError:
        try:
            import toml as _toml

            def loads(s: str) -> Dict[str, Any]:
                """Parse a TOML-formatted string into a dictionary.

                Uses the legacy ``toml`` third-party library as a last
                resort fallback.

                Args:
                    s: A string containing valid TOML.

                Returns:
                    Parsed configuration as a dictionary.

                Raises:
                    toml.TomlDecodeError: If the string is not valid TOML.

                Example:
                    >>> from config_stash.utils.toml_compat import loads
                    >>> config = loads('[server]\\nport = 8080')
                """
                return _toml.loads(s)

            def load_file(path: str) -> Dict[str, Any]:
                """Load and parse a TOML file into a dictionary.

                Uses the legacy ``toml`` third-party library as a last
                resort fallback.

                Args:
                    path: Path to a TOML file.

                Returns:
                    Parsed configuration as a dictionary.

                Raises:
                    FileNotFoundError: If the file does not exist.
                    toml.TomlDecodeError: If the file is not valid TOML.

                Example:
                    >>> from config_stash.utils.toml_compat import load_file
                    >>> config = load_file("pyproject.toml")
                """
                with open(path, "r") as f:
                    return _toml.load(f)

            TomlDecodeError = _toml.TomlDecodeError

        except ImportError:
            raise ImportError(
                "No TOML library found. Install tomli (pip install tomli) "
                "or use Python 3.11+ which includes tomllib."
            )


def dumps(data: Dict[str, Any]) -> str:
    """Serialize a dictionary to a TOML-formatted string.

    Tries ``tomli_w`` first, then falls back to the legacy ``toml``
    package. At least one TOML writer must be installed.

    Args:
        data: Dictionary to serialize. All keys must be strings and
            values must be TOML-compatible types.

    Returns:
        A TOML-formatted string representation of the dictionary.

    Raises:
        ImportError: If neither ``tomli_w`` nor ``toml`` is installed.

    Example:
        >>> from config_stash.utils.toml_compat import dumps
        >>> print(dumps({"server": {"port": 8080}}))
        [server]
        port = 8080
    """
    try:
        import tomli_w

        return tomli_w.dumps(data)
    except ImportError:
        pass

    try:
        import toml as _toml

        return _toml.dumps(data)
    except ImportError:
        raise ImportError(
            "No TOML writer found. Install tomli-w (pip install tomli-w) "
            "or toml (pip install toml) for TOML export support."
        )
