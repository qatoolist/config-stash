import toml
import importlib

def read_pyproject_config():
    try:
        with open("pyproject.toml", "r") as f:
            pyproject = toml.load(f)
        return pyproject.get("tool", {}).get("config_stash", {})
    except FileNotFoundError:
        print("No pyproject.toml file found in the current directory.")
        return {}

def get_default_loaders():
    config = read_pyproject_config()
    loader_definitions = config.get("loaders", {})
    loaders = {}
    for name, path in loader_definitions.items():
        module_name, class_name = path.split(":")
        module = importlib.import_module(module_name)
        loaders[name] = getattr(module, class_name)
    return loaders

def get_default_settings():
    config = read_pyproject_config()
    settings = {
        "default_environment": config.get("default_environment", "development"),
        "default_files": config.get("default_files", []),
        "default_prefix": config.get("default_prefix", "PREFIX"),
        "dynamic_reloading": config.get("dynamic_reloading", False)
    }
    return settings