#!/usr/bin/env python3
# pyright: basic
"""
Configuration Introspection API Examples

This example demonstrates the introspection and query capabilities
of Config-Stash, including keys(), has(), get(), schema(), and explain().
"""

import tempfile
import os

from config_stash import Config
from config_stash.loaders import YamlLoader


def example_keys_and_has():
    """Example 1: Listing keys and checking existence."""
    print("\n" + "=" * 70)
    print("Example 1: keys() and has() Methods")
    print("=" * 70)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
database:
  host: localhost
  port: 5432
  ssl:
    enabled: true
    cert: /path/to/cert.pem

api:
  endpoint: http://api.example.com
  timeout: 30
        """)
        config_file = f.name

    try:
        config = Config(loaders=[YamlLoader(config_file)], enable_ide_support=False)

        # List all configuration keys
        print("All configuration keys:")
        for key in sorted(config.keys()):
            print(f"  - {key}")

        # Check if keys exist
        print("\nChecking key existence:")
        print(f"  has('database'): {config.has('database')}")
        print(f"  has('database.host'): {config.has('database.host')}")
        print(f"  has('database.ssl.enabled'): {config.has('database.ssl.enabled')}")
        print(f"  has('nonexistent'): {config.has('nonexistent')}")

    finally:
        os.unlink(config_file)


def example_get_with_defaults():
    """Example 2: Safe value retrieval with defaults."""
    print("\n" + "=" * 70)
    print("Example 2: get() Method with Defaults")
    print("=" * 70)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
database:
  host: localhost
  port: 5432
        """)
        config_file = f.name

    try:
        config = Config(loaders=[YamlLoader(config_file)], enable_ide_support=False)

        # Get existing values
        print("Getting existing values:")
        print(f"  get('database.host'): {config.get('database.host')}")
        print(f"  get('database.port'): {config.get('database.port')}")

        # Get non-existent values with defaults
        print("\nGetting non-existent values with defaults:")
        print(f"  get('database.ssl', False): {config.get('database.ssl', False)}")
        print(f"  get('api.timeout', 30): {config.get('api.timeout', 30)}")
        print(f"  get('nonexistent', 'default'): {config.get('nonexistent', 'default')}")

    finally:
        os.unlink(config_file)


def example_schema_introspection():
    """Example 3: Getting schema information."""
    print("\n" + "=" * 70)
    print("Example 3: schema() Method")
    print("=" * 70)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
database:
  host: localhost
  port: 5432
  ssl:
    enabled: true

api:
  endpoint: http://api.example.com
  timeout: 30
        """)
        config_file = f.name

    try:
        config = Config(loaders=[YamlLoader(config_file)], enable_ide_support=False)

        # Get schema for entire configuration
        print("Full configuration schema:")
        full_schema = config.schema()
        print(f"  Type: {full_schema['type']}")
        print(f"  Keys: {full_schema['keys']}")

        # Get schema for specific key
        print("\nDatabase configuration schema:")
        db_schema = config.schema("database")
        print(f"  Type: {db_schema['type']}")
        print(f"  Keys: {db_schema['keys']}")

        # Get schema for nested key
        print("\nSSL configuration schema:")
        ssl_schema = config.schema("database.ssl")
        print(f"  Type: {ssl_schema['type']}")
        if ssl_schema['type'] == 'dict':
            print(f"  Keys: {ssl_schema['keys']}")

    finally:
        os.unlink(config_file)


def example_explain():
    """Example 4: Explaining configuration resolution."""
    print("\n" + "=" * 70)
    print("Example 4: explain() Method")
    print("=" * 70)

    # Create multiple config files to show resolution
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
database:
  host: localhost
  port: 5432
        """)
        base_file = f.name

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
database:
  port: 3306
  ssl: true
        """)
        override_file = f.name

    try:
        config = Config(
            loaders=[YamlLoader(base_file), YamlLoader(override_file)],
            enable_ide_support=False
        )

        # Explain how a value was resolved
        print("Explaining configuration resolution:")
        info = config.explain("database.port")
        print(f"  Key: database.port")
        print(f"  Value: {info.get('value')}")
        print(f"  Source: {info.get('source')}")
        if 'override_count' in info:
            print(f"  Override count: {info.get('override_count')}")

    finally:
        os.unlink(base_file)
        os.unlink(override_file)


def example_set():
    """Example 5: Programmatic configuration overrides."""
    print("\n" + "=" * 70)
    print("Example 5: set() Method for Overrides")
    print("=" * 70)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
database:
  host: localhost
  port: 5432
        """)
        config_file = f.name

    try:
        config = Config(loaders=[YamlLoader(config_file)], enable_ide_support=False)

        print("Original configuration:")
        print(f"  database.host: {config.get('database.host')}")
        print(f"  database.port: {config.get('database.port')}")

        # Override existing values
        config.set("database.host", "remote.db.example.com")
        config.set("database.port", 3306)

        # Set new values
        config.set("database.ssl", True)
        config.set("api.endpoint", "https://api.example.com")

        print("\nAfter overrides:")
        print(f"  database.host: {config.get('database.host')}")
        print(f"  database.port: {config.get('database.port')}")
        print(f"  database.ssl: {config.get('database.ssl')}")
        print(f"  api.endpoint: {config.get('api.endpoint')}")

    finally:
        os.unlink(config_file)


def main():
    """Run all introspection examples."""
    print("=" * 70)
    print("Config-Stash Introspection API Examples")
    print("=" * 70)

    example_keys_and_has()
    example_get_with_defaults()
    example_schema_introspection()
    example_explain()
    example_set()

    print("\n" + "=" * 70)
    print("All introspection examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
