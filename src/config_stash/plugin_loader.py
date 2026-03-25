from typing import Any

from config_stash.loader_manager import LoaderManager


def get_loader(name: str) -> Any:
    """Get a loader class by name, trying plugins first, then built-in loaders.

    Use this function when you need to resolve a loader at runtime by its
    short name (e.g., from a configuration file or CLI argument) rather than
    importing the class directly.

    Args:
        name: Short name of the loader.  Built-in names are ``"yaml"``,
            ``"json"``, ``"toml"``, ``"env"``, ``"envfile"``, and ``"ini"``.
            Plugin-registered names are checked first.

    Returns:
        The loader **class** (not an instance).  You must instantiate it
        yourself, passing the appropriate source path or arguments.

    Raises:
        ValueError: If no built-in or plugin loader matches ``name``.

    Example:
        >>> LoaderClass = get_loader("yaml")
        >>> loader = LoaderClass("config.yaml")
        >>> data = loader.load()
    """
    # Try plugins first
    loaders = LoaderManager.load_plugins()
    if name in loaders:
        return loaders[name]

    # Fall back to built-in loaders
    builtin_loaders = {
        "yaml": "config_stash.loaders.YamlLoader",
        "json": "config_stash.loaders.JsonLoader",
        "toml": "config_stash.loaders.TomlLoader",
        "env": "config_stash.loaders.EnvironmentLoader",
        "envfile": "config_stash.loaders.EnvFileLoader",
        "ini": "config_stash.loaders.IniLoader",
    }

    if name in builtin_loaders:
        module_path, class_name = builtin_loaders[name].rsplit(".", 1)
        import importlib

        module = importlib.import_module(module_path)
        return getattr(module, class_name)

    raise ValueError(f"Loader {name} not found")
