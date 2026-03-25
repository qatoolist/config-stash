"""Pydantic model validation for configurations."""
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportInvalidTypeForm=false
# pyright: reportGeneralTypeIssues=false

import logging
from typing import Any, Dict, Generic, Optional, Type, TypeVar

from config_stash.exceptions import ConfigValidationError

logger = logging.getLogger(__name__)

# pydantic is optional
try:
    from pydantic import BaseModel, ConfigDict, Field, ValidationError

    HAS_PYDANTIC = True
    T = TypeVar("T", bound=BaseModel)
except ImportError:
    HAS_PYDANTIC = False
    BaseModel = type
    T = TypeVar("T")  # type: ignore[misc]
    logger.warning("pydantic not installed. Pydantic validation disabled.")


class PydanticValidator(Generic[T]):
    """Validates configuration dictionaries using Pydantic models.

    PydanticValidator wraps a Pydantic ``BaseModel`` subclass and uses it
    to validate raw configuration dictionaries. It provides detailed,
    structured error reporting by converting Pydantic ``ValidationError``
    instances into ``ConfigValidationError`` with per-field error details.

    This validator is useful when you want strict, type-safe validation
    of your configuration with automatic coercion, default values, and
    nested model support provided by Pydantic.

    Attributes:
        model_class: The Pydantic model class used for validation.

    Example:
        >>> from pydantic import BaseModel, Field
        >>> from config_stash.validators import PydanticValidator
        >>>
        >>> class DBConfig(BaseModel):
        ...     host: str = "localhost"
        ...     port: int = Field(default=5432, ge=1, le=65535)
        ...     database: str
        >>>
        >>> validator = PydanticValidator(DBConfig)
        >>> model = validator.validate({"database": "mydb", "port": 3306})
        >>> print(model.host)  # "localhost" (default applied)

    Note:
        Requires the ``pydantic`` package (v2+). Install it with::

            pip install pydantic
    """

    def __init__(self, model_class: Type[T]) -> None:
        """Initialize with a Pydantic model class.

        Args:
            model_class: Pydantic model class for validation

        Raises:
            ImportError: If pydantic is not installed
        """
        if not HAS_PYDANTIC:
            raise ImportError(
                "pydantic is required for model validation. " "Install with: pip install pydantic"
            )
        self.model_class: Type[T] = model_class

    def validate(self, config: Dict[str, Any]) -> T:
        """Validate configuration against Pydantic model.

        Args:
            config: Configuration dictionary

        Returns:
            Validated Pydantic model instance

        Raises:
            ConfigValidationError: If validation fails (wraps Pydantic ValidationError)
        """
        try:
            return self.model_class(**config)
        except ValidationError as e:
            logger.error(f"Pydantic validation failed: {e}")
            validation_errors = []
            for error in e.errors():
                error_msg = (
                    f"Field '{'.'.join(str(p) for p in error['loc'])}': "
                    f"{error['msg']} (type: {error['type']})"
                )
                logger.error(f"  {error_msg}")
                validation_errors.append(
                    {
                        "loc": error["loc"],
                        "msg": error["msg"],
                        "type": error["type"],
                        "input": error.get("input"),
                    }
                )

            # Convert Pydantic ValidationError to ConfigValidationError
            raise ConfigValidationError(
                f"Configuration validation failed: {e}",
                validation_errors=validation_errors,
                original_error=e,
            ) from e

    def validate_to_dict(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and return as dictionary with defaults applied.

        This is a convenience method that validates the configuration and
        immediately serializes the resulting model back to a dictionary.
        The returned dictionary includes all default values defined in
        the Pydantic model, making it suitable for merging back into the
        configuration pipeline.

        Args:
            config: Configuration dictionary to validate.

        Returns:
            Validated configuration as a plain dictionary with all model
            defaults applied.

        Raises:
            ConfigValidationError: If validation fails.

        Example:
            >>> validator = PydanticValidator(DBConfig)
            >>> result = validator.validate_to_dict({"database": "mydb"})
            >>> print(result)
            {'host': 'localhost', 'port': 5432, 'database': 'mydb', ...}
        """
        model: Any = self.validate(config)
        return model.model_dump()


# Example Pydantic models for configuration
if HAS_PYDANTIC:

    class DatabaseConfig(BaseModel):
        """Database configuration model."""

        model_config = ConfigDict(extra="forbid")  # Don't allow extra fields

        host: str = Field(default="localhost", description="Database host")
        port: int = Field(default=5432, ge=1, le=65535, description="Database port")
        database: str = Field(..., description="Database name")
        username: str = Field(..., description="Database username")
        password: Optional[str] = Field(default=None, description="Database password")
        pool_size: int = Field(default=10, ge=1, le=100, description="Connection pool size")
        ssl: bool = Field(default=False, description="Enable SSL")

    class RedisConfig(BaseModel):
        """Redis configuration model."""

        host: str = Field(default="localhost")
        port: int = Field(default=6379, ge=1, le=65535)
        db: int = Field(default=0, ge=0)
        password: Optional[str] = None
        max_connections: int = Field(default=50, ge=1)

    class AppConfig(BaseModel):
        """Complete application configuration."""

        model_config = ConfigDict(extra="allow")  # Allow extra fields for extensibility

        app_name: str = Field(..., description="Application name")
        debug: bool = Field(default=False)
        log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
        database: DatabaseConfig
        redis: Optional[RedisConfig] = None
