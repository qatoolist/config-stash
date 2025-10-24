import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class EnvironmentHandler:
    """Handles environment-specific configuration merging."""

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
        for key, value in new.items():
            if isinstance(value, dict) and key in base:
                base[key] = self._merge_dicts(base[key], value)
            else:
                base[key] = value
        return base
