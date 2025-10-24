from config_stash.loader_manager import LoaderManager


def get_loader(name):
    """Get a loader by name, trying plugins first, then built-in loaders."""
    # Try plugins first
    loaders = LoaderManager.load_plugins()
    if name in loaders:
        return loaders[name]

    # Fall back to built-in loaders
    builtin_loaders = {
        'yaml': 'config_stash.loaders.YamlLoader',
        'json': 'config_stash.loaders.JsonLoader',
        'toml': 'config_stash.loaders.TomlLoader',
        'env': 'config_stash.loaders.EnvironmentLoader',
        'envfile': 'config_stash.loaders.EnvFileLoader',
        'ini': 'config_stash.loaders.IniLoader',
    }

    if name in builtin_loaders:
        module_path, class_name = builtin_loaders[name].rsplit('.', 1)
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, class_name)

    raise ValueError(f"Loader {name} not found")
