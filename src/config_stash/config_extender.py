from config_stash.config_loader import ConfigLoader
from config_stash.config_merger import ConfigMerger
from config_stash.environment_handler import EnvironmentHandler
from config_stash.attribute_accessor import AttributeAccessor

class ConfigExtender:
    def __init__(self, config):
        self.config = config

    def extend_config(self, loader):
        """Extend the configuration by loading and merging additional configurations using the specified loader."""
        try:
            config_loader = ConfigLoader([loader])
            new_config, source = config_loader.add_loader(loader)
            self.config.merged_config = ConfigMerger.merge_configs([(self.config.merged_config, ""), (new_config, source)])
            self.config.env_config = EnvironmentHandler(self.config.env, self.config.merged_config).get_env_config()
            self.config.attribute_accessor = AttributeAccessor(self.config.env_config)
            self.config.loader_manager.loaders.append(loader)
        except Exception as e:
            raise RuntimeError(f"Failed to extend configuration: {e}")