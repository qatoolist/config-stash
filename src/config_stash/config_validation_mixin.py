"""Validation mixin for Config.

Provides schema validation using Pydantic models or JSON Schema dictionaries.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ConfigValidation:
    """Mixin providing schema validation capabilities for Config."""

    # Declared by Config.__init__ — available via mixin composition
    _schema: Optional[Any]
    env_config: Dict[str, Any]
    merged_config: Dict[str, Any]
    _validated_model: Optional[Any]
    strict_validation: bool
    validate_on_load: bool

    def _validate_config(self) -> None:
        """Validate configuration against the provided schema.

        This is called automatically if validate_on_load is True.

        Raises:
            ConfigValidationError: If validation fails and strict_validation is True
        """
        if not self._schema:
            return

        config_dict = self.env_config if self.env_config else self.merged_config

        try:
            # Check if schema is a Pydantic model class
            is_pydantic = False
            try:
                from pydantic import BaseModel

                is_pydantic = isinstance(self._schema, type) and issubclass(
                    self._schema, BaseModel
                )
            except ImportError:
                pass

            if is_pydantic:
                from config_stash.validators.pydantic_validator import PydanticValidator

                validator = PydanticValidator(self._schema)
                self._validated_model = validator.validate(config_dict)
                logger.info(
                    "Configuration validated successfully against Pydantic model"
                )
            elif isinstance(self._schema, dict):
                # JSON Schema validation
                from config_stash.validators.schema_validator import SchemaValidator

                validator = SchemaValidator(self._schema)
                validator.validate(config_dict)
                logger.info("Configuration validated successfully against JSON Schema")
            else:
                logger.warning(f"Unknown schema type: {type(self._schema)}")
        except Exception as e:
            error_msg = f"Configuration validation failed: {e}"
            if self.strict_validation:
                from config_stash.exceptions import ConfigValidationError

                validation_errors = []
                if hasattr(e, "errors"):
                    validation_errors = list(getattr(e, "errors")())
                elif hasattr(e, "message"):
                    validation_errors = [{"message": str(getattr(e, "message"))}]

                raise ConfigValidationError(
                    error_msg,
                    schema_path=None,
                    validation_errors=validation_errors,
                    original_error=e,
                ) from e
            else:
                logger.warning(error_msg)

    def validate(self, schema: Optional[Any] = None) -> bool:
        """Validate configuration against a schema.

        Args:
            schema: Optional schema to validate against. If not provided,
                   uses the schema provided during Config initialization.
                   Can be a Pydantic model class or JSON Schema dictionary.

        Returns:
            True if valid, False otherwise

        Raises:
            ConfigValidationError: If validation fails and strict_validation is True

        Example:
            >>> from pydantic import BaseModel
            >>> class AppConfig(BaseModel):
            ...     database_url: str
            >>> config = Config(loaders=[YamlLoader("config.yaml")])
            >>> is_valid = config.validate(schema=AppConfig)
        """
        if not self.env_config and not self.merged_config:
            return False

        validation_schema = schema or self._schema

        if not validation_schema:
            return True

        original_schema = self._schema
        original_validate_on_load = self.validate_on_load
        original_strict = self.strict_validation

        try:
            self._schema = validation_schema
            self.validate_on_load = True
            self.strict_validation = True
            self._validate_config()
            return True
        except Exception:
            return False
        finally:
            self._schema = original_schema
            self.validate_on_load = original_validate_on_load
            self.strict_validation = original_strict
