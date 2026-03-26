#!/usr/bin/env python3
"""Typed Config — Config[T] for full IDE autocomplete and type safety.

This is the North Star feature of Config-Stash: load configuration from
any source (YAML, JSON, env vars, SSM, etc.) and access it with full
Pydantic type safety.

    config = Config[AppConfig](schema=AppConfig, validate_on_load=True, ...)
    config.typed.database.host   # IDE knows this is str
    config.typed.database.port   # IDE knows this is int
    config.typed.nonexistent     # mypy/pyright error at dev time
"""

import json
import os
import tempfile

import yaml


def example_basic_typed():
    """Example 1: Basic typed config access."""
    print("\n" + "=" * 70)
    print("Example 1: Basic Typed Config")
    print("=" * 70)

    try:
        from pydantic import BaseModel
    except ImportError:
        print("  pydantic not installed — skipping")
        return

    from cs import Config
    from cs.loaders import YamlLoader

    # Define your config schema as a Pydantic model
    class AppConfig(BaseModel):
        host: str
        port: int = 5432
        debug: bool = False

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"default": {"host": "localhost", "port": 8080, "debug": True}}, f)
        config_file = f.name

    try:
        # Config[AppConfig] gives you full type safety
        config = Config[AppConfig](
            env="default",
            loaders=[YamlLoader(config_file)],
            schema=AppConfig,
            validate_on_load=True,
            dynamic_reloading=False,
        )

        # .typed returns the validated Pydantic model
        print(f"  host: {config.typed.host} (type: {type(config.typed.host).__name__})")
        print(f"  port: {config.typed.port} (type: {type(config.typed.port).__name__})")
        print(
            f"  debug: {config.typed.debug} (type: {type(config.typed.debug).__name__})"
        )

        # Untyped access still works
        print(f"  config.host (untyped): {config.host}")

    finally:
        os.unlink(config_file)


def example_nested_models():
    """Example 2: Nested Pydantic models."""
    print("\n" + "=" * 70)
    print("Example 2: Nested Pydantic Models")
    print("=" * 70)

    try:
        from pydantic import BaseModel
    except ImportError:
        print("  pydantic not installed — skipping")
        return

    from cs import Config
    from cs.loaders import YamlLoader

    class DatabaseConfig(BaseModel):
        host: str = "localhost"
        port: int = 5432
        ssl: bool = False

    class CacheConfig(BaseModel):
        backend: str = "redis"
        ttl: int = 300

    class AppConfig(BaseModel):
        database: DatabaseConfig
        cache: CacheConfig
        app_name: str = "myapp"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(
            {
                "default": {
                    "database": {"host": "prod.db.com", "port": 3306, "ssl": True},
                    "cache": {"backend": "memcached", "ttl": 600},
                    "app_name": "production-app",
                }
            },
            f,
        )
        config_file = f.name

    try:
        config = Config[AppConfig](
            env="default",
            loaders=[YamlLoader(config_file)],
            schema=AppConfig,
            validate_on_load=True,
            dynamic_reloading=False,
        )

        # Full autocomplete on nested models
        db = config.typed.database
        print(f"  DB: {db.host}:{db.port} (ssl={db.ssl})")
        print(f"  Cache: {config.typed.cache.backend} (ttl={config.typed.cache.ttl})")
        print(f"  App: {config.typed.app_name}")

    finally:
        os.unlink(config_file)


def example_multi_source_typed():
    """Example 3: Multi-source loading with typed access."""
    print("\n" + "=" * 70)
    print("Example 3: Multi-Source Loading + Typed Access")
    print("=" * 70)

    try:
        from pydantic import BaseModel
    except ImportError:
        print("  pydantic not installed — skipping")
        return

    from cs import Config
    from cs.loaders import JsonLoader, YamlLoader

    class ServiceConfig(BaseModel):
        host: str
        port: int
        timeout: int = 30
        retries: int = 3

    # Base config in YAML
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"default": {"host": "localhost", "port": 8080, "timeout": 10}}, f)
        yaml_file = f.name

    # Override in JSON
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"default": {"host": "api.prod.com", "retries": 5}}, f)
        json_file = f.name

    try:
        config = Config[ServiceConfig](
            env="default",
            loaders=[YamlLoader(yaml_file), JsonLoader(json_file)],
            schema=ServiceConfig,
            validate_on_load=True,
            deep_merge=True,
            dynamic_reloading=False,
        )

        s = config.typed
        print(f"  host: {s.host} (from JSON override)")
        print(f"  port: {s.port} (from YAML base)")
        print(f"  timeout: {s.timeout} (from YAML base)")
        print(f"  retries: {s.retries} (from JSON override)")

    finally:
        os.unlink(yaml_file)
        os.unlink(json_file)


def example_typed_vs_untyped():
    """Example 4: Side-by-side comparison."""
    print("\n" + "=" * 70)
    print("Example 4: Typed vs Untyped — Side by Side")
    print("=" * 70)

    try:
        from pydantic import BaseModel
    except ImportError:
        print("  pydantic not installed — skipping")
        return

    from cs import Config
    from cs.loaders import YamlLoader

    class DbConfig(BaseModel):
        host: str
        port: int

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"default": {"host": "db.example.com", "port": 5432}}, f)
        config_file = f.name

    try:
        config = Config[DbConfig](
            env="default",
            loaders=[YamlLoader(config_file)],
            schema=DbConfig,
            validate_on_load=True,
            dynamic_reloading=False,
        )

        print("  UNTYPED (config.host):")
        print(f"    value: {config.host}")
        print(f"    type at runtime: {type(config.host).__name__}")
        print("    IDE type: Any (no autocomplete)")

        print("\n  TYPED (config.typed.host):")
        print(f"    value: {config.typed.host}")
        print(f"    type at runtime: {type(config.typed.host).__name__}")
        print("    IDE type: str (full autocomplete + mypy checking)")

    finally:
        os.unlink(config_file)


def main():
    print("=" * 70)
    print("  Config[T] — Type-Safe Configuration Access")
    print("  The North Star feature of Config-Stash")
    print("=" * 70)

    example_basic_typed()
    example_nested_models()
    example_multi_source_typed()
    example_typed_vs_untyped()

    print("\n" + "=" * 70)
    print("  All typed config examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
