class SourceTracker:
    def __init__(self, loaders):
        self.loaders = loaders

    def get_source(self, key):
        keys = key.split('.')
        for loader in reversed(self.loaders):
            source_config = loader.config
            try:
                for k in keys:
                    source_config = source_config[k]
                return loader.source
            except KeyError:
                continue
        return None  # Key not found