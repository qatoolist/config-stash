from config_stash.loader_manager import LoaderManager

def get_loader(name):
    loaders = LoaderManager.load_plugins()
    if name in loaders:
        return loaders[name]
    else:
        raise ValueError(f"Loader {name} not found")