class ConfigLoader:
    def __init__(self, loaders):
        self.loaders = loaders

    def load_configs(self):
        configs = []
        for loader in self.loaders:
            config = loader.load()
            configs.append((config, loader.source))
        return configs

    def add_loader(self, loader):
        config = loader.load()
        return config, loader.source