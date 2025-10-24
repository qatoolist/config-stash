"""Configuration export functionality for Config-Stash."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import toml
import yaml

logger = logging.getLogger(__name__)


class ConfigExporter:
    """Export configurations to various formats."""

    @staticmethod
    def to_dict(config) -> Dict[str, Any]:
        """Export configuration as dictionary.

        Args:
            config: Config instance

        Returns:
            Configuration dictionary
        """
        return config.env_config if hasattr(config, "env_config") else {}

    @staticmethod
    def to_json(config, indent: int = 2) -> str:
        """Export configuration as JSON string.

        Args:
            config: Config instance
            indent: JSON indentation level

        Returns:
            JSON string
        """
        return json.dumps(ConfigExporter.to_dict(config), indent=indent)

    @staticmethod
    def to_yaml(config, default_flow_style: bool = False) -> str:
        """Export configuration as YAML string.

        Args:
            config: Config instance
            default_flow_style: YAML flow style

        Returns:
            YAML string
        """
        return yaml.dump(
            ConfigExporter.to_dict(config),
            default_flow_style=default_flow_style,
            allow_unicode=True,
        )

    @staticmethod
    def to_toml(config) -> str:
        """Export configuration as TOML string.

        Args:
            config: Config instance

        Returns:
            TOML string
        """
        return toml.dumps(ConfigExporter.to_dict(config))

    @staticmethod
    def to_env(config, prefix: str = "", separator: str = "_") -> str:
        """Export configuration as environment variables.

        Args:
            config: Config instance
            prefix: Prefix for environment variables
            separator: Separator for nested keys

        Returns:
            Environment variable string
        """

        def flatten_dict(d: Dict, parent_key: str = "") -> Dict[str, str]:
            items = []
            for k, v in d.items():
                new_key = f"{parent_key}{separator}{k}".upper() if parent_key else k.upper()
                if isinstance(v, dict):
                    items.extend(flatten_dict(v, new_key).items())
                elif isinstance(v, (list, tuple)):
                    items.append((new_key, json.dumps(v)))
                elif isinstance(v, bool):
                    items.append((new_key, str(v).lower()))
                elif v is None:
                    items.append((new_key, ""))
                else:
                    items.append((new_key, str(v)))
            return dict(items)

        config_dict = ConfigExporter.to_dict(config)
        flat_dict = flatten_dict(config_dict, prefix)

        return "\n".join(f"{k}={v}" for k, v in sorted(flat_dict.items()))

    @staticmethod
    def dump(config, file_path: str, format: Optional[str] = None) -> None:
        """Dump configuration to file.

        Args:
            config: Config instance
            file_path: Output file path
            format: Output format (json, yaml, toml, env). Auto-detected if None.

        Raises:
            ValueError: If format is unknown
        """
        file_path = Path(file_path)

        # Auto-detect format from extension
        if format is None:
            ext = file_path.suffix.lower()
            # Special case for .env files (which may not have a suffix)
            if file_path.name.startswith(".env"):
                format = "env"
            else:
                format_map = {
                    ".json": "json",
                    ".yaml": "yaml",
                    ".yml": "yaml",
                    ".toml": "toml",
                    ".env": "env",
                }
                format = format_map.get(ext, "json")

        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Export based on format
        exporters = {
            "json": ConfigExporter.to_json,
            "yaml": ConfigExporter.to_yaml,
            "toml": ConfigExporter.to_toml,
            "env": ConfigExporter.to_env,
        }

        if format not in exporters:
            raise ValueError(f"Unknown format: {format}. Supported: {list(exporters.keys())}")

        content = exporters[format](config)

        with open(file_path, "w") as f:
            f.write(content)

        logger.info(f"Configuration exported to {file_path} (format: {format})")

    @staticmethod
    def diff(config1, config2, format: str = "json") -> str:
        """Generate diff between two configurations.

        Args:
            config1: First Config instance
            config2: Second Config instance
            format: Output format for diff

        Returns:
            Diff string
        """
        dict1 = ConfigExporter.to_dict(config1)
        dict2 = ConfigExporter.to_dict(config2)

        def dict_diff(d1: Dict, d2: Dict, path: str = "") -> Dict[str, Any]:
            diff = {}

            # Check for added/modified keys
            for key in d2:
                new_path = f"{path}.{key}" if path else key

                if key not in d1:
                    diff[f"+ {new_path}"] = d2[key]
                elif d1[key] != d2[key]:
                    if isinstance(d1[key], dict) and isinstance(d2[key], dict):
                        nested_diff = dict_diff(d1[key], d2[key], new_path)
                        diff.update(nested_diff)
                    else:
                        diff[f"~ {new_path}"] = {"old": d1[key], "new": d2[key]}

            # Check for removed keys
            for key in d1:
                if key not in d2:
                    new_path = f"{path}.{key}" if path else key
                    diff[f"- {new_path}"] = d1[key]

            return diff

        diff_dict = dict_diff(dict1, dict2)

        if format == "json":
            return json.dumps(diff_dict, indent=2)
        elif format == "yaml":
            return yaml.dump(diff_dict, default_flow_style=False)
        else:
            return str(diff_dict)


# Add export methods to Config class
def add_export_methods(config_class):
    """Add export methods to Config class.

    This function monkey-patches the Config class to add export methods.
    """
    config_class.to_dict = lambda self: ConfigExporter.to_dict(self)
    config_class.to_json = lambda self, indent=2: ConfigExporter.to_json(self, indent)
    config_class.to_yaml = lambda self: ConfigExporter.to_yaml(self)
    config_class.to_toml = lambda self: ConfigExporter.to_toml(self)
    config_class.to_env = lambda self, prefix="", separator="_": ConfigExporter.to_env(
        self, prefix, separator
    )
    config_class.dump = lambda self, file_path, format=None: ConfigExporter.dump(
        self, file_path, format
    )

    logger.debug("Export methods added to Config class")
