"""Tests for Pydantic model validation."""

import unittest
from typing import Optional

# Try to import pydantic
try:
    from pydantic import BaseModel, Field

    from config_stash.exceptions import ConfigValidationError
    from config_stash.validators.pydantic_validator import (
        AppConfig,
        DatabaseConfig,
        PydanticValidator,
        RedisConfig,
    )

    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False


@unittest.skipUnless(HAS_PYDANTIC, "pydantic not installed")
class TestPydanticValidator(unittest.TestCase):
    """Test cases for PydanticValidator."""

    def setUp(self):
        """Set up test fixtures."""
        if not HAS_PYDANTIC:
            return

        # Define test models
        class SimpleConfig(BaseModel):
            name: str
            age: int = Field(ge=0, le=150)
            email: Optional[str] = None

        class ServerConfig(BaseModel):
            host: str = "localhost"
            port: int = Field(default=8080, ge=1, le=65535)
            ssl: bool = False

        self.SimpleConfig = SimpleConfig
        self.ServerConfig = ServerConfig

    def test_valid_model(self):
        """Test validation with valid data."""
        validator = PydanticValidator(self.SimpleConfig)
        config = {"name": "John Doe", "age": 30, "email": "john@example.com"}
        result = validator.validate(config)

        self.assertEqual(result.name, "John Doe")
        self.assertEqual(result.age, 30)
        self.assertEqual(result.email, "john@example.com")

    def test_missing_required_field(self):
        """Test validation fails when required field is missing."""
        validator = PydanticValidator(self.SimpleConfig)
        config = {"age": 30}  # Missing required 'name'

        with self.assertRaises(ConfigValidationError) as context:
            validator.validate(config)

        errors = context.exception.validation_errors
        self.assertTrue(any(e.get("loc") == ("name",) or e.get("loc") == ["name"] for e in errors))

    def test_type_validation(self):
        """Test that types are validated correctly."""
        validator = PydanticValidator(self.SimpleConfig)
        config = {"name": "John", "age": "thirty"}  # Should be integer

        with self.assertRaises(ConfigValidationError):
            validator.validate(config)

    def test_field_constraints(self):
        """Test field value constraints."""
        validator = PydanticValidator(self.SimpleConfig)

        # Age too high
        config = {"name": "John", "age": 200}
        with self.assertRaises(ConfigValidationError):
            validator.validate(config)

        # Age negative
        config = {"name": "John", "age": -5}
        with self.assertRaises(ConfigValidationError):
            validator.validate(config)

    def test_default_values(self):
        """Test that default values are applied."""
        validator = PydanticValidator(self.ServerConfig)
        config = {}  # All defaults
        result = validator.validate(config)

        self.assertEqual(result.host, "localhost")
        self.assertEqual(result.port, 8080)
        self.assertEqual(result.ssl, False)

    def test_partial_defaults(self):
        """Test partial override of defaults."""
        validator = PydanticValidator(self.ServerConfig)
        config = {"host": "example.com"}
        result = validator.validate(config)

        self.assertEqual(result.host, "example.com")  # User value
        self.assertEqual(result.port, 8080)  # Default
        self.assertEqual(result.ssl, False)  # Default

    def test_validate_to_dict(self):
        """Test conversion back to dictionary."""
        validator = PydanticValidator(self.ServerConfig)
        config = {"host": "api.example.com", "port": 443, "ssl": True}
        result_dict = validator.validate_to_dict(config)

        self.assertIsInstance(result_dict, dict)
        self.assertEqual(result_dict["host"], "api.example.com")
        self.assertEqual(result_dict["port"], 443)
        self.assertEqual(result_dict["ssl"], True)

    def test_database_config(self):
        """Test the provided DatabaseConfig model."""
        validator = PydanticValidator(DatabaseConfig)

        # Valid config
        config = {
            "database": "myapp",
            "username": "dbuser",
            "host": "db.example.com",
            "port": 5432,
            "password": "secret",
            "ssl": True,
        }
        result = validator.validate(config)

        self.assertEqual(result.database, "myapp")
        self.assertEqual(result.username, "dbuser")
        self.assertEqual(result.host, "db.example.com")
        self.assertEqual(result.port, 5432)
        self.assertEqual(result.ssl, True)

    def test_database_config_defaults(self):
        """Test DatabaseConfig with minimal required fields."""
        validator = PydanticValidator(DatabaseConfig)

        # Minimal config (only required fields)
        config = {"database": "testdb", "username": "testuser"}
        result = validator.validate(config)

        self.assertEqual(result.database, "testdb")
        self.assertEqual(result.username, "testuser")
        self.assertEqual(result.host, "localhost")  # Default
        self.assertEqual(result.port, 5432)  # Default
        self.assertEqual(result.pool_size, 10)  # Default
        self.assertEqual(result.ssl, False)  # Default
        self.assertIsNone(result.password)  # Optional, not provided

    def test_redis_config(self):
        """Test the provided RedisConfig model."""
        validator = PydanticValidator(RedisConfig)

        # Test with defaults
        config = {}
        result = validator.validate(config)

        self.assertEqual(result.host, "localhost")
        self.assertEqual(result.port, 6379)
        self.assertEqual(result.db, 0)
        self.assertIsNone(result.password)
        self.assertEqual(result.max_connections, 50)

    def test_app_config_nested(self):
        """Test the nested AppConfig model."""
        validator = PydanticValidator(AppConfig)

        config = {
            "app_name": "TestApp",
            "debug": True,
            "log_level": "DEBUG",
            "database": {"database": "appdb", "username": "appuser", "host": "db.test.com"},
            "redis": {"host": "redis.test.com", "db": 2},
        }
        result = validator.validate(config)

        self.assertEqual(result.app_name, "TestApp")
        self.assertEqual(result.debug, True)
        self.assertEqual(result.log_level, "DEBUG")
        self.assertEqual(result.database.database, "appdb")
        self.assertEqual(result.database.host, "db.test.com")
        self.assertEqual(result.redis.host, "redis.test.com")
        self.assertEqual(result.redis.db, 2)

    def test_app_config_without_redis(self):
        """Test AppConfig without optional redis field."""
        validator = PydanticValidator(AppConfig)

        config = {"app_name": "SimpleApp", "database": {"database": "simpledb", "username": "user"}}
        result = validator.validate(config)

        self.assertEqual(result.app_name, "SimpleApp")
        self.assertIsNone(result.redis)  # Optional field not provided

    def test_extra_fields_forbidden(self):
        """Test that extra fields are rejected when configured."""
        validator = PydanticValidator(DatabaseConfig)

        config = {
            "database": "mydb",
            "username": "user",
            "extra_field": "not allowed",  # Extra field
        }

        with self.assertRaises(ConfigValidationError) as context:
            validator.validate(config)

        errors = context.exception.validation_errors
        self.assertTrue(any("extra" in str(e).lower() for e in errors))

    def test_log_level_pattern(self):
        """Test log level pattern validation in AppConfig."""
        validator = PydanticValidator(AppConfig)

        # Invalid log level
        config = {
            "app_name": "TestApp",
            "log_level": "INVALID",  # Not in pattern
            "database": {"database": "db", "username": "user"},
        }

        with self.assertRaises(ConfigValidationError):
            validator.validate(config)


if __name__ == "__main__":
    unittest.main()
