import os

from config_stash.loaders.loader import Loader

class EnvironmentLoader(Loader):
    def __init__(self, prefix):
        super().__init__(source=f"environment:{prefix}")
        self.prefix = prefix.upper()
        self.config = {}

    def load(self):
        try:
            env_vars = {key: value for key, value in os.environ.items() if key.startswith(self.prefix)}
            for key, value in env_vars.items():
                nested_keys = key[len(self.prefix)+1:].split('__')
                self._set_nested_value(self.config, nested_keys, value)
        except Exception as e:
            raise RuntimeError(f"Unexpected error loading environment variables with prefix {self.prefix}: {e}")
        return self.config

    def _set_nested_value(self, config, keys, value):
        for key in keys[:-1]:
            config = config.setdefault(key.lower(), {})
        config[keys[-1].lower()] = value