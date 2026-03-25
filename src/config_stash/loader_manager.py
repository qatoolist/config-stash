import importlib.metadata


class LoaderManager:
    def __init__(self, loaders):
        self.loaders = loaders
        self.configs = []

    def _load_configs(self):
        import logging

        logger = logging.getLogger(__name__)
        for loader in self.loaders:
            try:
                config = loader.load()
                if config is not None:  # Only append if config was loaded successfully
                    self.configs.append((config, loader.source))
            except Exception as e:
                # Log warning but continue with other loaders
                logger.warning(f"Failed to load configuration from {loader.source}: {e}")
                continue

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
