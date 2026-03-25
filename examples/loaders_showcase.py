#!/usr/bin/env python3
# pyright: basic
"""Loader Showcase — demonstrates every config file format supported by Config-Stash."""

import json
import os
import tempfile
from pathlib import Path

from cs import Config
from cs.loaders import (
    EnvFileLoader,
    EnvironmentLoader,
    IniLoader,
    JsonLoader,
    TomlLoader,
    YamlLoader,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _header(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def _subheader(title: str) -> None:
    """Print a subsection header."""
    print(f"\n--- {title} ---")


def _print_dict(d: dict, indent: int = 0) -> None:
    """Pretty-print a dict with indentation."""
    pad = "  " * indent
    for key, value in d.items():
        if isinstance(value, dict):
            print(f"{pad}{key}:")
            _print_dict(value, indent + 1)
        else:
            print(f"{pad}{key}: {value!r}")


# ---------------------------------------------------------------------------
# 1. TOML loading
# ---------------------------------------------------------------------------

def example_toml_loading() -> None:
    """Load configuration from a TOML file with [database] and [app] sections."""
    _header("1. TOML Loading")

    toml_content = """\
[database]
host = "db.example.com"
port = 5432
name = "warehouse"
ssl  = true

[app]
name    = "inventory-service"
version = "2.4.1"
workers = 4
debug   = false
"""

    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".toml", delete=False
    )
    try:
        tmp.write(toml_content)
        tmp.close()

        config = Config(
            loaders=[TomlLoader(tmp.name)],
            enable_ide_support=False,
        )

        print(f"Database host : {config.database.host}")
        print(f"Database port : {config.database.port}")
        print(f"Database SSL  : {config.database.ssl}")
        print(f"App name      : {config.app.name}")
        print(f"App workers   : {config.app.workers}")
    finally:
        os.unlink(tmp.name)


# ---------------------------------------------------------------------------
# 2. INI loading
# ---------------------------------------------------------------------------

def example_ini_loading() -> None:
    """Load configuration from an INI file and show section-to-dict mapping."""
    _header("2. INI Loading")

    ini_content = """\
[server]
host = 0.0.0.0
port = 8080
workers = 2
debug = true

[logging]
level = INFO
file = /var/log/app.log
rotate = true

[cache]
backend = redis
ttl = 300
max_size = 1024
"""

    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".ini", delete=False
    )
    try:
        tmp.write(ini_content)
        tmp.close()

        config = Config(
            loaders=[IniLoader(tmp.name)],
            enable_ide_support=False,
        )

        _subheader("Section -> dict mapping")
        print(f"server.host     : {config.server.host}")
        print(f"server.port     : {config.server.port}  (type: {type(config.server.port).__name__})")
        print(f"server.debug    : {config.server.debug}  (type: {type(config.server.debug).__name__})")
        print(f"logging.level   : {config.logging.level}")
        print(f"logging.rotate  : {config.logging.rotate}")
        print(f"cache.backend   : {config.cache.backend}")
        print(f"cache.ttl       : {config.cache.ttl}  (type: {type(config.cache.ttl).__name__})")
    finally:
        os.unlink(tmp.name)


# ---------------------------------------------------------------------------
# 3. .env file loading
# ---------------------------------------------------------------------------

def example_env_file_loading() -> None:
    """.env file loading with comments, quoting, nesting, and type coercion."""
    _header("3. .env File Loading")

    env_content = """\
# ── App settings ──────────────────────────────
APP_NAME="My Application"
APP_REGION='us-east-1'

# Inline comment after unquoted value
LOG_LEVEL=debug # this part is stripped

# ── Type coercion ─────────────────────────────
ENABLED=true
DISABLED=false
RETRIES=5
RATE=3.14
NEGATIVE=-42

# ── Dot-notation nesting ─────────────────────
database.host=localhost
database.port=5432
database.name=mydb
"""

    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".env", delete=False
    )
    try:
        tmp.write(env_content)
        tmp.close()

        config = Config(
            loaders=[EnvFileLoader(tmp.name)],
            enable_ide_support=False,
        )

        _subheader("Quoted values")
        print(f"APP_NAME   : {config.APP_NAME!r}  (double-quoted)")
        print(f"APP_REGION : {config.APP_REGION!r}  (single-quoted)")

        _subheader("Inline comment stripped")
        print(f"LOG_LEVEL  : {config.LOG_LEVEL!r}")

        _subheader("Type coercion")
        print(f"ENABLED    : {config.ENABLED!r}  (type: {type(config.ENABLED).__name__})")
        print(f"DISABLED   : {config.DISABLED!r}  (type: {type(config.DISABLED).__name__})")
        print(f"RETRIES    : {config.RETRIES!r}  (type: {type(config.RETRIES).__name__})")
        print(f"RATE       : {config.RATE!r}  (type: {type(config.RATE).__name__})")
        print(f"NEGATIVE   : {config.NEGATIVE!r}  (type: {type(config.NEGATIVE).__name__})")

        _subheader("Dot-notation nesting")
        print(f"database.host : {config.database.host}")
        print(f"database.port : {config.database.port}  (type: {type(config.database.port).__name__})")
        print(f"database.name : {config.database.name}")
    finally:
        os.unlink(tmp.name)


# ---------------------------------------------------------------------------
# 4. Environment variable loading
# ---------------------------------------------------------------------------

def example_environment_variable_loading() -> None:
    """Load env vars with a prefix; double-underscore becomes nested keys."""
    _header("4. Environment Variable Loading")

    env_vars = {
        "MYAPP_DATABASE__HOST": "prod.db.example.com",
        "MYAPP_DATABASE__PORT": "5432",
        "MYAPP_DATABASE__SSL": "true",
        "MYAPP_CACHE__BACKEND": "redis",
        "MYAPP_CACHE__TTL": "600",
        "MYAPP_LOG_LEVEL": "warning",
    }

    for key, value in env_vars.items():
        os.environ[key] = value

    try:
        config = Config(
            loaders=[EnvironmentLoader("MYAPP", separator="__")],
            enable_ide_support=False,
        )

        _subheader("Nested keys created via double-underscore separator")
        print(f"database.host : {config.database.host}")
        print(f"database.port : {config.database.port}  (type: {type(config.database.port).__name__})")
        print(f"database.ssl  : {config.database.ssl}  (type: {type(config.database.ssl).__name__})")
        print(f"cache.backend : {config.cache.backend}")
        print(f"cache.ttl     : {config.cache.ttl}  (type: {type(config.cache.ttl).__name__})")

        _subheader("Single-level key (no separator)")
        print(f"log_level     : {config.log_level}")
    finally:
        for key in env_vars:
            os.environ.pop(key, None)


# ---------------------------------------------------------------------------
# 5. HTTP remote loading (conceptual)
# ---------------------------------------------------------------------------

def example_http_remote_loading() -> None:
    """Show HTTPLoader usage pattern. Not executed — requires a live server."""
    _header("5. HTTP Remote Loading (conceptual)")

    print(
        "HTTPLoader fetches config from any HTTP/HTTPS endpoint.\n"
        "It requires the 'requests' package.\n"
    )

    print("Usage pattern:\n")
    print("    from cs.loaders import HTTPLoader\n")
    print("    loader = HTTPLoader(")
    print('        url="https://config.internal.example.com/api/v1/config.json",')
    print("        timeout=10,")
    print('        headers={"Authorization": "Bearer <token>"},')
    print("    )")
    print("    config = Config(")
    print("        loaders=[loader],")
    print("        enable_ide_support=False,")
    print("    )")
    print("    print(config.database.host)\n")
    print(
        "The response body is parsed automatically based on the URL\n"
        "extension or Content-Type header (JSON, YAML, TOML supported)."
    )


# ---------------------------------------------------------------------------
# 6. Multi-source merge (deep merge)
# ---------------------------------------------------------------------------

def example_multi_source_merge() -> None:
    """Load YAML + JSON + env vars and show deep merge preserving nested keys."""
    _header("6. Multi-Source Merge (deep_merge=True)")

    yaml_content = """\
database:
  host: localhost
  port: 5432
  options:
    pool_size: 5
    timeout: 30

app:
  name: my-service
  version: "1.0.0"
"""

    json_content = json.dumps({
        "database": {
            "port": 3306,
            "options": {
                "ssl": True,
            },
        },
        "app": {
            "debug": True,
        },
    })

    yaml_tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    )
    json_tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    )

    env_vars = {
        "MERGE_DATABASE__OPTIONS__POOL_SIZE": "20",
    }
    for key, value in env_vars.items():
        os.environ[key] = value

    try:
        yaml_tmp.write(yaml_content)
        yaml_tmp.close()
        json_tmp.write(json_content)
        json_tmp.close()

        config = Config(
            loaders=[
                YamlLoader(yaml_tmp.name),
                JsonLoader(json_tmp.name),
                EnvironmentLoader("MERGE", separator="__"),
            ],
            deep_merge=True,
            enable_ide_support=False,
        )

        _subheader("Result after deep merge (YAML <- JSON <- env vars)")
        print(f"database.host               : {config.database.host}  (from YAML)")
        print(f"database.port               : {config.database.port}  (overridden by JSON)")
        print(f"database.options.pool_size   : {config.database.options.pool_size}  (overridden by env var)")
        print(f"database.options.timeout     : {config.database.options.timeout}  (preserved from YAML)")
        print(f"database.options.ssl         : {config.database.options.ssl}  (added by JSON)")
        print(f"app.name                    : {config.app.name}  (from YAML)")
        print(f"app.version                 : {config.app.version}  (from YAML)")
        print(f"app.debug                   : {config.app.debug}  (added by JSON)")
        print()
        print("Key insight: deep merge PRESERVES nested keys from earlier")
        print("sources while allowing later sources to override or extend them.")
    finally:
        os.unlink(yaml_tmp.name)
        os.unlink(json_tmp.name)
        for key in env_vars:
            os.environ.pop(key, None)


# ---------------------------------------------------------------------------
# 7. Shallow vs deep merge
# ---------------------------------------------------------------------------

def example_shallow_vs_deep_merge() -> None:
    """Show how shallow merge replaces entire sections instead of merging."""
    _header("7. Shallow vs Deep Merge")

    yaml_content = """\
database:
  host: localhost
  port: 5432
  options:
    pool_size: 5
    timeout: 30
"""

    json_content = json.dumps({
        "database": {
            "port": 3306,
            "options": {
                "ssl": True,
            },
        },
    })

    yaml_tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    )
    json_tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    )

    try:
        yaml_tmp.write(yaml_content)
        yaml_tmp.close()
        json_tmp.write(json_content)
        json_tmp.close()

        _subheader("deep_merge=True (default)")
        deep = Config(
            loaders=[YamlLoader(yaml_tmp.name), JsonLoader(json_tmp.name)],
            deep_merge=True,
            enable_ide_support=False,
        )
        _print_dict(deep.to_dict()["database"], indent=1)

        _subheader("deep_merge=False")
        shallow = Config(
            loaders=[YamlLoader(yaml_tmp.name), JsonLoader(json_tmp.name)],
            deep_merge=False,
            enable_ide_support=False,
        )
        _print_dict(shallow.to_dict()["database"], indent=1)

        print()
        print("Key insight: with deep_merge=False the JSON source's 'database'")
        print("dict REPLACES the YAML 'database' dict entirely — host, and the")
        print("original pool_size/timeout options are lost.")
    finally:
        os.unlink(yaml_tmp.name)
        os.unlink(json_tmp.name)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    """Run all loader showcase examples."""
    print("=" * 70)
    print("  Config-Stash  —  Loader Showcase")
    print("=" * 70)

    examples = [
        ("TOML loading", example_toml_loading),
        ("INI loading", example_ini_loading),
        (".env file loading", example_env_file_loading),
        ("Environment variable loading", example_environment_variable_loading),
        ("HTTP remote loading (conceptual)", example_http_remote_loading),
        ("Multi-source deep merge", example_multi_source_merge),
        ("Shallow vs deep merge", example_shallow_vs_deep_merge),
    ]

    passed = 0
    failed = 0

    for name, fn in examples:
        try:
            fn()
            passed += 1
        except Exception as exc:
            failed += 1
            print(f"\n[ERROR] {name} failed: {exc}")

    print(f"\n{'=' * 70}")
    print(f"  Done — {passed} passed, {failed} failed")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
