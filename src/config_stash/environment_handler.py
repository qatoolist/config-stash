class EnvironmentHandler:
    def __init__(self, env, config):
        self.env = env
        self.config = config

    def get_env_config(self):
        if self.env in self.config:
            return self._merge_dicts(self.config['default'], self.config[self.env])
        else:
            return self.config['default']

    def _merge_dicts(self, base, new):
        for key, value in new.items():
            if isinstance(value, dict) and key in base:
                base[key] = self._merge_dicts(base[key], value)
            else:
                base[key] = value
        return base