"""JSON Schema validation for configurations."""

# pyright: reportPossiblyUnboundVariable=false

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
    """Validates configuration dictionaries against a JSON Schema.

    SchemaValidator uses the ``jsonschema`` library to validate configuration
    dictionaries against a JSON Schema (Draft 4 through Draft 7). It also
    supports applying default values defined in the schema to produce a
    complete configuration dictionary.

    This validator is ideal when you need a language-agnostic schema
    definition that can be shared across services written in different
    languages, or when you want to validate configuration without
    defining Python model classes.

    Attributes:
        schema: The JSON Schema dictionary used for validation.

    Example:
        >>> from config_stash.validators import SchemaValidator
        >>>
        >>> schema = {
        ...     "type": "object",
        ...     "properties": {
        ...         "host": {"type": "string", "default": "localhost"},
        ...         "port": {"type": "integer", "minimum": 1},
        ...     },
        ...     "required": ["port"],
        ... }
        >>> validator = SchemaValidator(schema)
        >>> validator.validate({"port": 8080})  # Returns True
        True

    Note:
        Requires the ``jsonschema`` package. Install it with::

            pip install jsonschema
    """

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

        First validates the configuration against the schema, then creates
        a deep copy and fills in any missing properties that have ``default``
        values defined in the schema. Nested object properties are handled
        recursively.

        Args:
            config: Configuration dictionary. This dictionary is **not**
                modified; a deep copy is returned.

        Returns:
            New configuration dictionary with schema defaults applied for
            any missing properties.

        Raises:
            ValidationError: If the configuration does not conform to the
                schema.

        Example:
            >>> schema = {
            ...     "type": "object",
            ...     "properties": {
            ...         "host": {"type": "string", "default": "localhost"},
            ...         "port": {"type": "integer", "default": 5432},
            ...         "database": {"type": "string"},
            ...     },
            ...     "required": ["database"],
            ... }
            >>> validator = SchemaValidator(schema)
            >>> result = validator.validate_with_defaults({"database": "mydb"})
            >>> print(result)
            {'database': 'mydb', 'host': 'localhost', 'port': 5432}
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
                logger.debug(
                    f"Applied default value for '{prop}': {prop_schema['default']}"
                )
            elif (
                prop in config
                and isinstance(config[prop], dict)
                and prop_schema.get("type") == "object"
            ):
                self._apply_defaults(config[prop], prop_schema)

    @classmethod
    def from_file(cls, schema_path: str) -> "SchemaValidator":
        """Create a SchemaValidator from a JSON schema file.

        Reads a JSON file from disk and uses its contents as the
        validation schema.

        Args:
            schema_path: Path to a JSON schema file.

        Returns:
            A new SchemaValidator instance configured with the loaded schema.

        Raises:
            FileNotFoundError: If the schema file does not exist.
            json.JSONDecodeError: If the file is not valid JSON.
            ImportError: If ``jsonschema`` is not installed.

        Example:
            >>> validator = SchemaValidator.from_file("schemas/app.schema.json")
            >>> validator.validate({"port": 8080})
            True
        """
        with open(schema_path, "r") as f:
            schema = json.load(f)
        return cls(schema)


# Example schema for database configuration
DATABASE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "host": {
            "type": "string",
            "description": "Database host",
            "default": "localhost",
        },
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
