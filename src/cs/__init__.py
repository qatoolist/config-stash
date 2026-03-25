"""cs — Short alias for config_stash.

Use `cs` anywhere you would use `config_stash`:

    from cs import Config
    from cs.loaders import YamlLoader, JsonLoader
    from cs.secret_stores import SecretResolver

This is a convenience alias — both `cs` and `config_stash` work identically.
"""

from config_stash import *  # noqa: F401,F403
from config_stash import __all__, __version__  # noqa: F401
