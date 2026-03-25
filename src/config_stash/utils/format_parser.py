"""Shared format detection and parsing utility for config content."""

import json
from typing import Any, Dict

from config_stash.exceptions import ConfigFormatError


def parse_config_content(content: str, filename: str) -> Dict[str, Any]:
    """Parse configuration content based on filename extension.

    Detects JSON, YAML, or TOML format from the filename extension
    and parses accordingly. Falls back to JSON if unrecognized.

    Args:
        content: Raw string content to parse
        filename: Filename or key used to detect format (by extension)

    Returns:
        Parsed configuration dictionary

    Raises:
        ConfigFormatError: If parsing fails
    """
    try:
        if filename.endswith(".json"):
            return json.loads(content)
        elif filename.endswith((".yaml", ".yml")):
            import yaml

            return yaml.safe_load(content) or {}
        elif filename.endswith(".toml"):
            from config_stash.utils.toml_compat import loads as toml_loads

            return toml_loads(content)
        else:
            # Default to JSON
            return json.loads(content)
    except Exception as e:
        raise ConfigFormatError(
            f"Failed to parse configuration content for {filename}: {e}",
            source=filename,
            original_error=e,
        ) from e
