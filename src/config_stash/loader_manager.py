import importlib.metadata


class LoaderManager:
    def __init__(self, loaders):
        self.loaders = loaders
        self.configs = []
        self._load_configs()

    def _load_configs(self):
        for loader in self.loaders:
            config = loader.load()
            self.configs.append((config, loader.source))

    def get_configs(self):
        return self.configs

    @staticmethod
    def load_plugins():
        loaders = {}
        # Python 3.10+ uses select() method, older versions use dict-like access
        try:
            eps = importlib.metadata.entry_points(group="config_stash.loaders")
        except TypeError:
            # Python < 3.10
            eps = importlib.metadata.entry_points().get("config_stash.loaders", [])

        for entry_point in eps:
            loaders[entry_point.name] = entry_point.load()
        return loaders
