#!/usr/bin/env python3
# pyright: basic
"""
Schema Validation Examples

This example demonstrates how to use schema validation with Config-Stash,
including Pydantic models and JSON Schema validation.
"""

import tempfile
import os

from config_stash import Config
from config_stash.loaders import YamlLoader


def example_1_pydantic_validation():
    """Example 1: Pydantic model validation."""
    print("\n" + "=" * 70)
    print("Example 1: Pydantic Model Validation")
    print("=" * 70)

    try:
        from pydantic import BaseModel, Field

        # Define Pydantic models
        class DatabaseConfig(BaseModel):
            host: str
            port: int = Field(ge=1, le=65535, default=5432)
            name: str
            ssl: bool = False

        class AppConfig(BaseModel):
            app_name: str
            database: DatabaseConfig
            debug: bool = False

        # Create config file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
app_name: MyApp
database:
  host: localhost
  port: 5432
  name: myapp_db
  ssl: true
debug: false
            """)
            config_file = f.name

        try:
            # Load with schema validation
            config = Config(
                loaders=[YamlLoader(config_file)],
                schema=AppConfig,
                validate_on_load=True,
                strict_validation=False,  # Don't raise on validation errors
                enable_ide_support=False
            )

            print("✅ Configuration validated successfully!")
            print(f"App name: {config.app_name}")
            print(f"Database host: {config.database.host}")
            print(f"Database port: {config.database.port}")

        finally:
            os.unlink(config_file)

    except ImportError:
        print("⚠️  Pydantic not installed. Install with: pip install pydantic")


def example_2_json_schema_validation():
    """Example 2: JSON Schema validation."""
    print("\n" + "=" * 70)
    print("Example 2: JSON Schema Validation")
    print("=" * 70)

    # Define JSON Schema
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "app_name": {"type": "string"},
            "port": {"type": "integer", "minimum": 1, "maximum": 65535, "default": 8080},
            "debug": {"type": "boolean", "default": False},
            "database": {
                "type": "object",
                "properties": {
                    "host": {"type": "string", "default": "localhost"},
                    "port": {"type": "integer", "default": 5432},
                },
                "required": ["host"],
            },
        },
        "required": ["app_name"],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("""
app_name: MyApp
port: 8080
database:
  host: localhost
  port: 5432
        """)
        config_file = f.name

    try:
        from config_stash.validators import SchemaValidator

        config = Config(
            loaders=[YamlLoader(config_file)],
            schema=schema,
            validate_on_load=True,
            enable_ide_support=False
        )

        print("✅ Configuration validated with JSON Schema!")
        print(f"App name: {config.app_name}")
        print(f"Port: {config.port}")
        print(f"Database host: {config.database.host}")

    finally:
        os.unlink(config_file)


def example_3_validation_with_defaults():
    """Example 3: Validation with default values."""
    print("\n" + "=" * 70)
    print("Example 3: Validation with Defaults")
    print("=" * 70)

    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "app_name": {"type": "string"},
            "port": {"type": "integer", "default": 8080},
            "debug": {"type": "boolean", "default": False},
        },
        "required": ["app_name"],
    }

    # Config file missing some fields with defaults
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("app_name: MyApp\n")
        config_file = f.name

    try:
        from config_stash.validators import SchemaValidator

        validator = SchemaValidator(schema)
        config_data = Config(loaders=[YamlLoader(config_file)], enable_ide_support=False).to_dict()

        # Validate and apply defaults
        validated = validator.validate_with_defaults(config_data)

        print("Configuration with defaults applied:")
        print(f"  app_name: {validated['app_name']}")
        print(f"  port: {validated.get('port')}")  # Should be 8080 (default)
        print(f"  debug: {validated.get('debug')}")  # Should be False (default)

    finally:
        os.unlink(config_file)


def main():
    """Run all validation examples."""
    print("=" * 70)
    print("Config-Stash Validation Examples")
    print("=" * 70)

    example_1_pydantic_validation()
    example_2_json_schema_validation()
    example_3_validation_with_defaults()

    print("\n" + "=" * 70)
    print("All validation examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
