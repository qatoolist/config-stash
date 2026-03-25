"""Configuration export functionality for Config-Stash."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml

from config_stash.utils.toml_compat import dumps as toml_dumps

logger = logging.getLogger(__name__)


class ConfigExporter:
    """Export configurations to various file and string formats.

    ConfigExporter provides static methods to serialize a Config instance
    into JSON, YAML, TOML, and .env formats. It can also write the
    serialized output directly to a file with automatic format detection
    based on the file extension, and generate diffs between two
    configurations.

    All methods are static and accept a Config instance as the first
    argument. The ``add_export_methods`` function patches these onto the
    Config class as convenience instance methods (e.g., ``config.to_json()``).

    Example:
        >>> from config_stash import Config
        >>> from config_stash.exporters import ConfigExporter
        >>>
        >>> config = Config(loaders=[YamlLoader("app.yaml")])
        >>> json_str = ConfigExporter.to_json(config)
        >>> ConfigExporter.dump(config, "output/config.yaml")
    """

    @staticmethod
    def to_dict(config: Any) -> Dict[str, Any]:
        """Export configuration as a plain dictionary.

        Args:
            config: Config instance with an ``env_config`` attribute.

        Returns:
            Configuration dictionary. Returns an empty dict if the
            config has no ``env_config`` attribute.

        Example:
            >>> data = ConfigExporter.to_dict(config)
            >>> print(data["database"]["host"])
            localhost
        """
        return config.env_config if hasattr(config, "env_config") else {}

    @staticmethod
    def to_json(config: Any, indent: int = 2) -> str:
        """Export configuration as a JSON string.

        Args:
            config: Config instance.
            indent: Number of spaces for JSON indentation. Defaults to 2.

        Returns:
            JSON-formatted string.

        Example:
            >>> json_str = ConfigExporter.to_json(config)
            >>> print(json_str)
            {
              "database": {
                "host": "localhost"
              }
            }
        """
        return json.dumps(ConfigExporter.to_dict(config), indent=indent)

    @staticmethod
    def to_yaml(config: Any, default_flow_style: bool = False) -> str:
        """Export configuration as a YAML string.

        Args:
            config: Config instance.
            default_flow_style: If True, use inline/flow style for
                collections. Defaults to False (block style).

        Returns:
            YAML-formatted string.

        Example:
            >>> yaml_str = ConfigExporter.to_yaml(config)
            >>> print(yaml_str)
            database:
              host: localhost
              port: 5432
        """
        return yaml.dump(
            ConfigExporter.to_dict(config),
            default_flow_style=default_flow_style,
            allow_unicode=True,
        )

    @staticmethod
    def to_toml(config: Any) -> str:
        """Export configuration as a TOML string.

        Args:
            config: Config instance.

        Returns:
            TOML-formatted string.

        Raises:
            ImportError: If no TOML writer (``tomli_w`` or ``toml``)
                is installed.

        Example:
            >>> toml_str = ConfigExporter.to_toml(config)
            >>> print(toml_str)
            [database]
            host = "localhost"
            port = 5432
        """
        return toml_dumps(ConfigExporter.to_dict(config))

    @staticmethod
    def to_env(config: Any, prefix: str = "", separator: str = "_") -> str:
        """Export configuration as a .env-formatted string.

        Flattens nested dictionaries into ``KEY=value`` lines suitable for
        shell sourcing or ``.env`` files. Keys are uppercased and nested
        keys are joined with the separator. Lists and tuples are serialized
        as JSON arrays; booleans become lowercase strings; None becomes
        an empty string.

        Args:
            config: Config instance.
            prefix: Optional prefix prepended to all keys (e.g., ``"APP"``
                produces ``APP_DATABASE_HOST``).
            separator: Separator between nested key segments. Defaults
                to ``"_"``.

        Returns:
            Newline-separated ``KEY=value`` string, sorted alphabetically.

        Example:
            >>> env_str = ConfigExporter.to_env(config, prefix="MYAPP")
            >>> print(env_str)
            MYAPP_DATABASE_HOST=localhost
            MYAPP_DATABASE_PORT=5432
        """

        def flatten_dict(d: Dict, parent_key: str = "") -> Dict[str, str]:
            items: List[Tuple[str, str]] = []
            for k, v in d.items():
                new_key = (
                    f"{parent_key}{separator}{k}".upper() if parent_key else k.upper()
                )
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
    def dump(
        config: Any, file_path: Union[str, Path], format: Optional[str] = None
    ) -> None:
        """Write configuration to a file in the specified format.

        The output format is auto-detected from the file extension when
        ``format`` is None. Parent directories are created automatically
        if they do not exist.

        Args:
            config: Config instance.
            file_path: Output file path (string or ``Path``).
            format: Output format -- one of ``"json"``, ``"yaml"``,
                ``"toml"``, or ``"env"``. Auto-detected from the file
                extension if None.

        Raises:
            ValueError: If the format is not recognized.

        Example:
            >>> ConfigExporter.dump(config, "output/config.yaml")
            >>> ConfigExporter.dump(config, "config.out", format="json")
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
        exporters: Dict[str, Any] = {
            "json": ConfigExporter.to_json,
            "yaml": ConfigExporter.to_yaml,
            "toml": ConfigExporter.to_toml,
            "env": ConfigExporter.to_env,
        }

        if format not in exporters:
            raise ValueError(
                f"Unknown format: {format}. Supported: {list(exporters.keys())}"
            )

        content = exporters[format](config)

        with open(file_path, "w") as f:
            f.write(content)

        logger.info(f"Configuration exported to {file_path} (format: {format})")

    @staticmethod
    def diff(config1: Any, config2: Any, format: str = "json") -> str:
        """Generate a diff between two configurations.

        Compares two Config instances and returns a structured diff
        showing added (``+``), removed (``-``), and modified (``~``)
        keys. Nested dictionaries are compared recursively.

        Args:
            config1: The baseline Config instance.
            config2: The updated Config instance to compare against.
            format: Output format for the diff -- ``"json"``, ``"yaml"``,
                or ``"str"`` (Python repr). Defaults to ``"json"``.

        Returns:
            Formatted diff string. Keys are prefixed with ``+`` (added),
            ``-`` (removed), or ``~`` (modified with old/new values).

        Example:
            >>> diff_str = ConfigExporter.diff(old_config, new_config)
            >>> print(diff_str)
            {
              "+ new_key": "value",
              "~ database.port": {"old": 5432, "new": 3306},
              "- removed_key": "old_value"
            }
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
def add_export_methods(config_class: type) -> None:
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
