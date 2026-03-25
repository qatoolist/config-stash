#!/usr/bin/env python3
# pyright: basic
"""
Async/Await Support Examples

This example demonstrates the async/await capabilities of Config-Stash
for use in asynchronous Python applications.
"""

import asyncio
import tempfile
import os

from config_stash.async_config import AsyncConfig, AsyncYamlLoader


async def example_1_basic_async():
    """Example 1: Basic async configuration loading."""
    print("\n" + "=" * 70)
    print("Example 1: Basic Async Configuration Loading")
    print("=" * 70)

    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
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
        # Create async config
        loader = AsyncYamlLoader(config_file)
        config = await AsyncConfig.create(env="production", loaders=[loader])

        # Access configuration values asynchronously
        host = await config.get_async("database.host")
        port = await config.get_async("database.port")
        endpoint = await config.get_async("api.endpoint")

        print(f"Database host: {host}")
        print(f"Database port: {port}")
        print(f"API endpoint: {endpoint}")

    finally:
        os.unlink(config_file)


async def example_2_parallel_loading():
    """Example 2: Loading multiple configurations in parallel."""
    print("\n" + "=" * 70)
    print("Example 2: Parallel Configuration Loading")
    print("=" * 70)

    # Create multiple config files
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("database:\n  host: localhost\n")
        config1_file = f.name

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("api:\n  endpoint: http://api.example.com\n")
        config2_file = f.name

    try:
        # Load multiple configs in parallel (happens automatically)
        loaders = [
            AsyncYamlLoader(config1_file),
            AsyncYamlLoader(config2_file)
        ]
        config = await AsyncConfig.create(env="production", loaders=loaders)

        # Access merged configuration
        host = await config.get_async("database.host")
        endpoint = await config.get_async("api.endpoint")

        print(f"Database host: {host}")
        print(f"API endpoint: {endpoint}")

    finally:
        os.unlink(config1_file)
        os.unlink(config2_file)


async def example_3_async_reload():
    """Example 3: Asynchronous configuration reloading."""
    print("\n" + "=" * 70)
    print("Example 3: Async Configuration Reloading")
    print("=" * 70)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
database:
  host: localhost
  port: 5432
        """)
        config_file = f.name

    try:
        loader = AsyncYamlLoader(config_file)
        config = await AsyncConfig.create(env="production", loaders=[loader])

        print("Initial configuration:")
        print(f"  Host: {await config.get_async('database.host')}")

        # Modify config file
        with open(config_file, 'w') as f:
            f.write("""
database:
  host: remote.db.example.com
  port: 3306
            """)

        # Reload configuration
        await config.reload()

        print("\nAfter reload:")
        print(f"  Host: {await config.get_async('database.host')}")
        print(f"  Port: {await config.get_async('database.port')}")

    finally:
        os.unlink(config_file)


async def example_4_async_validation():
    """Example 4: Asynchronous configuration validation."""
    print("\n" + "=" * 70)
    print("Example 4: Async Configuration Validation")
    print("=" * 70)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
database:
  host: localhost
  port: 5432
        """)
        config_file = f.name

    try:
        loader = AsyncYamlLoader(config_file)
        config = await AsyncConfig.create(env="production", loaders=[loader])

        # Validate configuration (schema would be passed here)
        is_valid = await config.validate_async(schema=None)
        print(f"Configuration is valid: {is_valid}")

    finally:
        os.unlink(config_file)


async def main():
    """Run all async examples."""
    print("=" * 70)
    print("Config-Stash Async/Await Examples")
    print("=" * 70)

    await example_1_basic_async()
    await example_2_parallel_loading()
    await example_3_async_reload()
    await example_4_async_validation()

    print("\n" + "=" * 70)
    print("All async examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
