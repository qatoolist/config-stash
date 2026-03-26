#!/usr/bin/env python3
"""
Basic Usage Examples for Config-Stash

This example demonstrates the fundamental features and usage patterns
of Config-Stash for new users.
"""

import os
import tempfile
from pathlib import Path

from config_stash import Config
from config_stash.loaders import YamlLoader, JsonLoader, EnvironmentLoader


def example_1_simple_config():
    """Example 1: Loading configuration from a single file."""
    print("\n" + "=" * 70)
    print("Example 1: Simple Configuration Loading")
    print("=" * 70)

    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("""
database:
  host: localhost
  port: 5432
  name: myapp

api:
  endpoint: http://api.example.com
  timeout: 30
        """)
        config_file = f.name

    try:
        # Load configuration
        config = Config(loaders=[YamlLoader(config_file)])

        # Access configuration values using attribute-style access
        print(f"Database host: {config.database.host}")
        print(f"Database port: {config.database.port}")
        print(f"API endpoint: {config.api.endpoint}")

    finally:
        os.unlink(config_file)


def example_2_multiple_sources():
    """Example 2: Loading configuration from multiple sources."""
    print("\n" + "=" * 70)
    print("Example 2: Multiple Configuration Sources")
    print("=" * 70)

    # Create base config
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("""
database:
  host: localhost
  port: 5432
        """)
        base_file = f.name

    # Create override config
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        import json
        json.dump({
            "database": {
                "port": 3306,
                "ssl": True
            }
        }, f)
        override_file = f.name

    try:
        # Load from multiple sources (later sources override earlier ones)
        config = Config(
            loaders=[
                YamlLoader(base_file),
                JsonLoader(override_file)
            ]
        )

        print(f"Database host: {config.database.host}")  # From base
        print(f"Database port: {config.database.port}")  # Overridden
        print(f"Database SSL: {config.database.ssl}")    # From override

    finally:
        os.unlink(base_file)
        os.unlink(override_file)


def example_3_environment_variables():
    """Example 3: Using environment variables."""
    print("\n" + "=" * 70)
    print("Example 3: Environment Variables")
    print("=" * 70)

    # Set environment variables (in real usage, set these externally)
    os.environ["APP_DATABASE__HOST"] = "prod.db.example.com"
    os.environ["APP_DATABASE__PORT"] = "5432"
    os.environ["APP_API__TIMEOUT"] = "60"

    try:
        # Load from environment with prefix 'APP'
        config = Config(
            loaders=[EnvironmentLoader("APP", separator="__")]
        )

        print(f"Database host: {config.database.host}")
        print(f"Database port: {config.database.port}")
        print(f"API timeout: {config.api.timeout}")

    finally:
        # Clean up
        for key in ["APP_DATABASE__HOST", "APP_DATABASE__PORT", "APP_API__TIMEOUT"]:
            os.environ.pop(key, None)


def example_4_environment_specific():
    """Example 4: Environment-specific configurations."""
    print("\n" + "=" * 70)
    print("Example 4: Environment-Specific Configurations")
    print("=" * 70)

    # Create config with multiple environments
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("""
development:
  database:
    host: localhost
    port: 5432
    debug: true

production:
  database:
    host: prod.db.example.com
    port: 3306
    debug: false
        """)
        config_file = f.name

    try:
        # Load development config
        dev_config = Config(
            env="development",
            loaders=[YamlLoader(config_file)]
        )
        print("Development config:")
        print(f"  Host: {dev_config.database.host}")
        print(f"  Port: {dev_config.database.port}")
        print(f"  Debug: {dev_config.database.debug}")

        # Load production config
        prod_config = Config(
            env="production",
            loaders=[YamlLoader(config_file)]
        )
        print("\nProduction config:")
        print(f"  Host: {prod_config.database.host}")
        print(f"  Port: {prod_config.database.port}")
        print(f"  Debug: {prod_config.database.debug}")

    finally:
        os.unlink(config_file)


def example_5_config_builder():
    """Example 5: Using ConfigBuilder for fluent configuration."""
    print("\n" + "=" * 70)
    print("Example 5: ConfigBuilder Pattern")
    print("=" * 70)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("""
database:
  host: localhost
  port: 5432
        """)
        config_file = f.name

    try:
        from config_stash import ConfigBuilder

        # Build configuration using fluent API
        config = (ConfigBuilder()
                  .with_env("production")
                  .add_loader(YamlLoader(config_file))
                  .enable_deep_merge()
                  .build())

        print(f"Database host: {config.database.host}")
        print(f"Database port: {config.database.port}")

    finally:
        os.unlink(config_file)


def main():
    """Run all basic examples."""
    print("=" * 70)
    print("Config-Stash Basic Usage Examples")
    print("=" * 70)

    example_1_simple_config()
    example_2_multiple_sources()
    example_3_environment_variables()
    example_4_environment_specific()
    example_5_config_builder()

    print("\n" + "=" * 70)
    print("All basic examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
