"""JSON Schema validation for configurations."""

import json
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# jsonschema is optional
try:
    import jsonschema
    from jsonschema import ValidationError, validate

    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False
    logger.warning("jsonschema not installed. Schema validation disabled.")


class SchemaValidator:
    """Validates configuration against JSON Schema."""

    def __init__(self, schema: Dict[str, Any]):
        """Initialize with a JSON Schema.

        Args:
            schema: JSON Schema dictionary

        Raises:
            ImportError: If jsonschema is not installed
        """
        if not HAS_JSONSCHEMA:
            raise ImportError(
                "jsonschema is required for schema validation. "
                "Install with: pip install jsonschema"
            )
        self.schema = schema

    def validate(self, config: Dict[str, Any]) -> bool:
        """Validate configuration against schema.

        Args:
            config: Configuration dictionary to validate

        Returns:
            True if valid

        Raises:
            ValidationError: If validation fails
        """
        try:
            validate(instance=config, schema=self.schema)
            return True
        except ValidationError as e:
            logger.error(f"Schema validation failed: {e.message}")
            logger.error(f"Failed at path: {'.'.join(str(p) for p in e.path)}")
            raise

    def validate_with_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and apply default values from schema.

        Args:
            config: Configuration dictionary (not modified)

        Returns:
            New configuration dict with defaults applied
        """
        import copy

        # First validate
        self.validate(config)

        # Work on a copy to avoid mutating the input
        result = copy.deepcopy(config)

        # Apply defaults from schema recursively
        self._apply_defaults(result, self.schema)

        return result

    def _apply_defaults(self, config: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Recursively apply default values from schema properties.

        Args:
            config: Configuration dictionary to apply defaults to (mutated in-place)
            schema: Schema dictionary with properties and defaults
        """
        if "properties" not in schema:
            return

        for prop, prop_schema in schema["properties"].items():
            if prop not in config and "default" in prop_schema:
                config[prop] = prop_schema["default"]
                logger.debug(f"Applied default value for '{prop}': {prop_schema['default']}")
            elif prop in config and isinstance(config[prop], dict) and prop_schema.get("type") == "object":
                self._apply_defaults(config[prop], prop_schema)

    @classmethod
    def from_file(cls, schema_path: str) -> "SchemaValidator":
        """Create validator from schema file.

        Args:
            schema_path: Path to JSON schema file

        Returns:
            SchemaValidator instance
        """
        with open(schema_path, "r") as f:
            schema = json.load(f)
        return cls(schema)


# Example schema for database configuration
DATABASE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "host": {"type": "string", "description": "Database host", "default": "localhost"},
        "port": {"type": "integer", "minimum": 1, "maximum": 65535, "default": 5432},
        "database": {"type": "string", "description": "Database name"},
        "username": {"type": "string", "description": "Database username"},
        "password": {"type": "string", "description": "Database password"},
        "pool_size": {"type": "integer", "minimum": 1, "maximum": 100, "default": 10},
        "ssl": {"type": "boolean", "default": False},
    },
    "required": ["database", "username"],
    "additionalProperties": False,
}
