from typing import Any, Dict, List, Optional, Tuple

from config_stash.loaders.loader import Loader


class ConfigLoader:
    """Manages loading of configurations from multiple loader sources.

    This class coordinates the loading of configurations from a list of
    loaders, handling the collection and source tracking of loaded configs.
    """

    def __init__(self, loaders: List[Loader]) -> None:
        """Initialize the configuration loader.

        Args:
            loaders: List of Loader instances to use for loading configurations
        """
        self.loaders: List[Loader] = loaders

    def load_configs(self) -> List[Tuple[Optional[Dict[str, Any]], str]]:
        """Load configurations from all registered loaders.

        Returns:
            List of (configuration_dict, source) tuples. Configuration dict
            may be None if a loader couldn't load its source (depending on
            loader behavior).

        Example:
            >>> loaders = [YamlLoader("config.yaml"), JsonLoader("config.json")]
            >>> loader = ConfigLoader(loaders)
            >>> configs = loader.load_configs()
            >>> # Returns: [(config_dict, "config.yaml"), (config_dict, "config.json")]
        """
        configs: List[Tuple[Optional[Dict[str, Any]], str]] = []
        for loader in self.loaders:
            config = loader.load()
            configs.append((config, loader.source))
        return configs

    def add_loader(self, loader: Loader) -> Tuple[Optional[Dict[str, Any]], str]:
        """Load configuration from a single loader.

        Args:
            loader: Loader instance to load configuration from

        Returns:
            Tuple of (configuration_dict, source). Configuration dict may be
            None if the loader couldn't load its source.
        """
        config = loader.load()
        return config, loader.source
