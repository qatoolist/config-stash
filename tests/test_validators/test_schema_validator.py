"""Tests for JSON Schema validation."""

import json
import tempfile
import unittest
from pathlib import Path

from config_stash.validators.schema_validator import SchemaValidator


class TestSchemaValidator(unittest.TestCase):
    """Test cases for SchemaValidator."""

    def setUp(self):
        """Set up test fixtures."""
        self.simple_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer", "minimum": 0, "maximum": 150},
                "email": {"type": "string", "format": "email"},
            },
            "required": ["name"],
        }

        self.schema_with_defaults = {
            "type": "object",
            "properties": {
                "host": {"type": "string", "default": "localhost"},
                "port": {"type": "integer", "default": 8080},
                "debug": {"type": "boolean", "default": False},
            },
        }

        self.nested_schema = {
            "type": "object",
            "properties": {
                "database": {
                    "type": "object",
                    "properties": {
                        "host": {"type": "string"},
                        "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                    },
                    "required": ["host"],
                }
            },
        }

    def test_valid_config(self):
        """Test validation with valid configuration."""
        validator = SchemaValidator(self.simple_schema)
        config = {"name": "John Doe", "age": 30, "email": "john@example.com"}
        self.assertTrue(validator.validate(config))

    def test_missing_required_field(self):
        """Test validation fails when required field is missing."""
        validator = SchemaValidator(self.simple_schema)
        config = {"age": 30}
        with self.assertRaises(Exception):  # Would be ValidationError with jsonschema
            validator.validate(config)

    def test_invalid_type(self):
        """Test validation fails with wrong type."""
        validator = SchemaValidator(self.simple_schema)
        config = {"name": "John", "age": "thirty"}  # Should be integer
        with self.assertRaises(Exception):
            validator.validate(config)

    def test_apply_defaults(self):
        """Test that default values are applied."""
        validator = SchemaValidator(self.schema_with_defaults)
        config = {}
        result = validator.validate_with_defaults(config)

        self.assertEqual(result.get("host"), "localhost")
        self.assertEqual(result.get("port"), 8080)
        self.assertEqual(result.get("debug"), False)

    def test_partial_defaults(self):
        """Test that defaults are applied only for missing fields."""
        validator = SchemaValidator(self.schema_with_defaults)
        config = {"host": "example.com"}
        result = validator.validate_with_defaults(config)

        self.assertEqual(result.get("host"), "example.com")  # User value preserved
        self.assertEqual(result.get("port"), 8080)  # Default applied
        self.assertEqual(result.get("debug"), False)  # Default applied

    def test_nested_validation(self):
        """Test validation of nested objects."""
        validator = SchemaValidator(self.nested_schema)

        # Valid nested config
        valid_config = {"database": {"host": "localhost", "port": 5432}}
        self.assertTrue(validator.validate(valid_config))

        # Invalid nested config (port out of range)
        invalid_config = {"database": {"host": "localhost", "port": 99999}}
        with self.assertRaises(Exception):
            validator.validate(invalid_config)

    def test_from_file(self):
        """Test loading schema from file."""
        # Create temporary schema file
        schema_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(self.simple_schema, schema_file)
        schema_file.close()

        try:
            validator = SchemaValidator.from_file(schema_file.name)
            config = {"name": "Test User"}
            self.assertTrue(validator.validate(config))
        finally:
            Path(schema_file.name).unlink()

    def test_additional_properties(self):
        """Test handling of additional properties."""
        strict_schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "additionalProperties": False,
        }

        validator = SchemaValidator(strict_schema)

        # Should fail with extra property
        config = {"name": "Test", "extra": "not allowed"}
        with self.assertRaises(Exception):
            validator.validate(config)

    def test_number_constraints(self):
        """Test number minimum and maximum constraints."""
        schema = {
            "type": "object",
            "properties": {"percentage": {"type": "number", "minimum": 0, "maximum": 100}},
        }

        validator = SchemaValidator(schema)

        # Valid percentage
        self.assertTrue(validator.validate({"percentage": 50}))

        # Invalid: too low
        with self.assertRaises(Exception):
            validator.validate({"percentage": -10})

        # Invalid: too high
        with self.assertRaises(Exception):
            validator.validate({"percentage": 150})

    def test_string_patterns(self):
        """Test string pattern validation."""
        schema = {
            "type": "object",
            "properties": {"username": {"type": "string", "pattern": "^[a-zA-Z0-9_]+$"}},
        }

        validator = SchemaValidator(schema)

        # Valid username
        self.assertTrue(validator.validate({"username": "user_123"}))

        # Invalid username (contains special char)
        with self.assertRaises(Exception):
            validator.validate({"username": "user@123"})


if __name__ == "__main__":
    unittest.main()
