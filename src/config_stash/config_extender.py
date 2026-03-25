from typing import TYPE_CHECKING

from config_stash.config_loader import ConfigLoader
from config_stash.config_merger import ConfigMerger
from config_stash.environment_handler import EnvironmentHandler
from config_stash.exceptions import ConfigLoadError
from config_stash.loaders.loader import Loader

if TYPE_CHECKING:
    from config_stash.config import Config


class ConfigExtender:
    """Handles extending existing configuration with additional loaders.

    This class provides functionality to dynamically add new configuration
    sources to an already-initialized Config instance.
    """

    def __init__(self, config: "Config") -> None:
        """Initialize the config extender.

        Args:
            config: The Config instance to extend
        """
        self.config = config

    def extend_config(self, loader: Loader) -> None:
        """Extend the configuration by loading and merging additional configurations.

        This method loads configuration from the provided loader and merges
        it into the existing configuration, updating both merged_config and
        env_config.

        Args:
            loader: Loader instance to load additional configuration from

        Raises:
            ConfigLoadError: If loading or merging fails
        """
        try:
            config_loader = ConfigLoader([loader])
            new_config, source = config_loader.add_loader(loader)

            if new_config is None:
                # Loader returned None - skip this extension
                return

            # Merge with existing config
            self.config.merged_config = ConfigMerger.merge_configs(
                [(self.config.merged_config, ""), (new_config, source)],
                deep_merge=self.config.deep_merge,
            )

            # Update environment-specific config
            self.config.env_config = EnvironmentHandler(
                self.config.env, self.config.merged_config
            ).get_env_config()

            # Rebuild derived state
            self.config._rebuild_state()

            # Add loader to the manager's list
            self.config.loader_manager.loaders.append(loader)
        except ConfigLoadError:
            # Re-raise ConfigLoadError as-is
            raise
        except Exception as e:
            raise ConfigLoadError(
                f"Failed to extend configuration with loader {loader.source}",
                source=loader.source,
                loader_type=loader.__class__.__name__,
                original_error=e,
            ) from e
