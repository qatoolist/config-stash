"""TOML compatibility layer.

Uses stdlib tomllib (Python 3.11+) or tomli as fallback.
Falls back to the deprecated toml package as a last resort.
"""

import sys
from typing import Any, Dict

# Try stdlib first (Python 3.11+), then tomli, then legacy toml
if sys.version_info >= (3, 11):
    import tomllib

    def loads(s: str) -> Dict[str, Any]:
        return tomllib.loads(s)

    def load_file(path: str) -> Dict[str, Any]:
        with open(path, "rb") as f:
            return tomllib.load(f)

    TomlDecodeError = tomllib.TOMLDecodeError

else:
    try:
        import tomli

        def loads(s: str) -> Dict[str, Any]:
            return tomli.loads(s)

        def load_file(path: str) -> Dict[str, Any]:
            with open(path, "rb") as f:
                return tomli.load(f)

        TomlDecodeError = tomli.TOMLDecodeError

    except ImportError:
        try:
            import toml as _toml

            def loads(s: str) -> Dict[str, Any]:
                return _toml.loads(s)

            def load_file(path: str) -> Dict[str, Any]:
                with open(path, "r") as f:
                    return _toml.load(f)

            TomlDecodeError = _toml.TomlDecodeError

        except ImportError:
            raise ImportError(
                "No TOML library found. Install tomli (pip install tomli) "
                "or use Python 3.11+ which includes tomllib."
            )


def dumps(data: Dict[str, Any]) -> str:
    """Serialize a dict to TOML string.

    Uses tomli_w if available, falls back to legacy toml package.
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
