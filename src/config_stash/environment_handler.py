import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class EnvironmentHandler:
    """Handles environment-specific configuration merging.

    Given a configuration dictionary that contains a ``default`` section and
    optional environment-specific sections, this class merges the default
    values with the values for the active environment.  Keys in the
    environment section override those in ``default``; nested dictionaries
    are deep-merged.

    If the configuration is flat (no ``default`` or environment sections),
    it is returned as-is.

    Example:
        >>> config = {
        ...     "default": {"database": {"host": "localhost", "port": 5432}},
        ...     "production": {"database": {"host": "db.prod.internal"}},
        ... }
        >>> handler = EnvironmentHandler(env="production", config=config)
        >>> handler.get_env_config()
        {'database': {'host': 'db.prod.internal', 'port': 5432}}
    """

    def __init__(self, env: Optional[str], config: Dict[str, Any]) -> None:
        """Initialize the environment handler.

        Args:
            env: Environment name (e.g., 'development', 'production')
            config: Configuration dictionary with environment sections
        """
        self.env = env
        self.config = config

    def get_env_config(self) -> Dict[str, Any]:
        """Get the merged configuration for the current environment.

        Returns:
            Merged configuration dictionary for the environment
        """
        # If no environment structure exists (e.g., flat config from EnvironmentLoader),
        # return the entire config
        if "default" not in self.config and (
            not self.env or self.env not in self.config
        ):
            # Flat configuration without environment sections
            return self.config.copy()

        # Check if environment exists and warn if not
        if self.env and self.env != "default" and self.env not in self.config:
            available_envs = [k for k in self.config.keys() if k != "default"]
            logger.warning(
                f"Environment '{self.env}' not found in configuration. "
                f"Available environments: {available_envs}. "
                f"Using 'default' configuration as fallback."
            )

        # Get base configuration
        base_config = self.config.get("default", {}).copy()

        # Merge with environment-specific config if it exists
        if self.env and self.env in self.config:
            return self._merge_dicts(base_config, self.config[self.env])

        return base_config

    def _merge_dicts(self, base, new):
        from config_stash.utils.dict_utils import deep_merge_dicts

        return deep_merge_dicts(base, new)
