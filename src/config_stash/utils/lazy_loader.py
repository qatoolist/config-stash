from functools import lru_cache

class LazyLoader:
    def __init__(self, config):
        self.config = config

    @lru_cache(maxsize=128)
    def get(self, key):
        keys = key.split('.')
        value = self.config
        for k in keys:
            value = value[k]
        return value