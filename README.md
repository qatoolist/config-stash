# Config-Stash

![Config-Stash Logo](./logo/config-stash.png)

<div align="center">

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE.txt)
[![CI Status](https://img.shields.io/github/actions/workflow/status/qatoolist/config-stash/ci.yml?branch=main)](https://github.com/qatoolist/config-stash/actions)
[![PyPI Version](https://img.shields.io/pypi/v/config-stash)](https://pypi.org/project/config-stash/)

**A comprehensive, production-ready configuration management library for Python**

[Installation](#installation) • [Quick Start](#quick-start) • [Features](#features) • [Examples](examples/) • [Documentation](#documentation)

</div>

---

## Overview

**Config-Stash** is a modern, feature-rich configuration management library designed for Python applications. It provides a unified interface for loading, merging, validating, and accessing configuration from multiple sources with enterprise-grade features like secret management, schema validation, observability, versioning, and async support.

### Why Config-Stash?

- 🎯 **Unified Interface** - Single API for all configuration sources
- 🔐 **Secret Management** - Built-in support for AWS, Azure, GCP, Vault
- ✅ **Type Safety** - Full type hints and Pydantic/JSON Schema validation
- 🔄 **Dynamic Reloading** - Hot reload with incremental updates
- 📊 **Observability** - Metrics, tracing, and event emission
- 🚀 **Async Support** - Async/await API for non-blocking config loading
- 🎨 **Developer Experience** - IDE autocomplete, debugging tools, CLI
- 🏢 **Enterprise Ready** - Versioning, drift detection, advanced merging

---

## Installation

```bash
# Basic installation
pip install config-stash

# With optional dependencies
pip install config-stash[watch]         # File watching for dynamic reloading
pip install config-stash[cli]           # CLI tools (config-stash command)
pip install config-stash[validation]    # Schema validation (Pydantic, JSON Schema)
pip install config-stash[cloud]         # Cloud storage support (AWS S3, Azure, GCP)
pip install config-stash[secrets]       # Secret store support (AWS, Azure, GCP, Vault)
pip install config-stash[all]           # All features
```

**Requirements:** Python 3.9+

📖 **See [examples/basic_usage.py](examples/basic_usage.py) for getting started**

---

## Quick Start

### Basic Usage

```python
from config_stash import Config
from config_stash.loaders import YamlLoader

# Load from a single file
config = Config(loaders=[YamlLoader("config.yaml")])

# Access configuration values with attribute-style syntax
print(config.database.host)
print(config.database.port)
```

### Multiple Sources

```python
from config_stash import Config
from config_stash.loaders import YamlLoader, EnvironmentLoader

# Load from multiple sources (later sources override earlier ones)
config = Config(
    env="production",
    loaders=[
        YamlLoader("config/base.yaml"),
        YamlLoader("config/production.yaml"),
        EnvironmentLoader("APP"),  # APP_* environment variables
    ]
)
```

### With Secret Stores

```python
from config_stash import Config
from config_stash.secret_stores import AWSSecretsManager, SecretResolver
from config_stash.loaders import YamlLoader

# Initialize secret store
secret_store = AWSSecretsManager(region_name='us-east-1')

# Use with Config
config = Config(
    loaders=[YamlLoader("config.yaml")],
    secret_resolver=SecretResolver(secret_store)
)

# Secrets in config.yaml like "${secret:db/password}" are automatically resolved
print(config.database.password)  # Resolved from AWS Secrets Manager
```

📖 **See [examples/basic_usage.py](examples/basic_usage.py) for more examples**

---

## Features

### 🎯 Core Features

#### Multiple Configuration Sources

- **Files**: JSON, YAML, TOML, INI, .env
- **Cloud Storage**: AWS S3, Azure Blob, Google Cloud Storage, IBM COS
- **Remote**: HTTP/HTTPS endpoints, Git repositories
- **Environment Variables**: System environment with prefix support
- **Secret Stores**: AWS, Azure, GCP, HashiCorp Vault
- **Custom Loaders**: Extensible loader interface

#### Schema Validation

```python
from config_stash import Config
from config_stash.loaders import YamlLoader
from pydantic import BaseModel

class DatabaseConfig(BaseModel):
    host: str
    port: int = 5432

config = Config(
    loaders=[YamlLoader("config.yaml")],
    schema=DatabaseConfig,
    validate_on_load=True
)
```

📖 **See [examples/validation_example.py](examples/validation_example.py)**

#### Dynamic Reloading

> Requires `pip install config-stash[watch]` for file watching.

```python
config = Config(
    loaders=[YamlLoader("config.yaml")],
    dynamic_reloading=True  # Watches files for changes
)

# Config automatically reloads when files change
# Or manually reload with incremental updates (no watchdog needed)
config.reload(incremental=True)  # Only reloads changed files
```

#### Introspection API

```python
# List all keys
keys = config.keys()

# Check if key exists
exists = config.has("database.host")

# Get value with default
value = config.get("database.host", "localhost")

# Get schema information
schema = config.schema("database")

# Explain how a value was resolved
info = config.explain("database.host")
```

📖 **See [examples/introspection_api.py](examples/introspection_api.py)**

#### Configuration Overrides

```python
# Programmatic overrides
config.set("database.host", "remote.db.example.com")
config.set("database.port", 3306)

# Or via CLI
# config-stash load production --override "database.host=remote.db.example.com"
```

### 🔐 Secret Store Integration

**Comprehensive secret management with automatic resolution:**

```python
from config_stash.secret_stores import (
    AWSSecretsManager,
    HashiCorpVault,
    AzureKeyVault,
    GCPSecretManager,
    SecretResolver
)

# AWS Secrets Manager
store = AWSSecretsManager(region_name='us-east-1')

# HashiCorp Vault with OIDC + Kerberos (SSO)
from config_stash.secret_stores.vault_auth import OIDCAuth
auth = OIDCAuth(role='myapp-role', use_kerberos=True)
store = HashiCorpVault(url='https://vault.example.com', auth_method=auth)

# Multi-store fallback
from config_stash.secret_stores import MultiSecretStore, DictSecretStore
store = MultiSecretStore([
    DictSecretStore({"local/key": "override"}),  # Highest priority
    AWSSecretsManager(region_name='us-east-1'),  # Production
])

config = Config(
    loaders=[YamlLoader("config.yaml")],
    secret_resolver=SecretResolver(store)
)
```

**Configuration file with secret placeholders:**
```yaml
database:
  host: prod-db.example.com
  password: "${secret:prod/database/password}"
api:
  key: "${secret:prod/api/key:api_key}"  # JSON path extraction
```

**Supported Secret Stores:**
- ✅ **AWS Secrets Manager** - Native AWS secret management
- ✅ **HashiCorp Vault** - Enterprise secrets with 10+ auth methods
  - OIDC with Kerberos (SSO, no browser if `kinit` done)
  - LDAP with PIN+Token (complex password policies)
  - JWT, Kubernetes, AWS, Azure, GCP, AppRole, Token
- ✅ **Azure Key Vault** - Azure native secret management
- ✅ **GCP Secret Manager** - Google Cloud secret management
- ✅ **Environment Variables** - Simple env-based secrets
- ✅ **Multi-Store** - Combine multiple stores with fallback hierarchy

📖 **See [examples/secret_store_example.py](examples/secret_store_example.py) and [docs/SECRET_STORES.md](docs/SECRET_STORES.md)**

### 🚀 Advanced Features

#### Async/Await Support

```python
from config_stash.async_config import AsyncConfig, AsyncYamlLoader

async def main():
    loader = AsyncYamlLoader("config.yaml")
    config = await AsyncConfig.create(loaders=[loader])
    value = await config.get_async("database.host")
```

📖 **See [examples/async_example.py](examples/async_example.py)**

#### Configuration Versioning

```python
# Enable versioning
version_manager = config.enable_versioning()

# Save current configuration as a version
version = config.save_version(metadata={
    "author": "user@example.com",
    "message": "Updated database config"
})

# Rollback to a previous version
config.rollback_to_version(version.version_id)

# List all versions
versions = version_manager.list_versions(limit=10)
```

#### Configuration Diff & Drift Detection

```python
# Compare two configurations
config1 = Config(loaders=[YamlLoader("dev.yaml")])
config2 = Config(loaders=[YamlLoader("prod.yaml")])
diffs = config1.diff(config2)

for diff in diffs:
    print(f"{diff.path}: {diff.diff_type.value}")

# Detect configuration drift
intended = Config(loaders=[YamlLoader("intended.yaml")])
actual = Config(loaders=[YamlLoader("actual.yaml")])
drift = actual.detect_drift(intended)
```

#### Observability & Metrics

```python
# Enable metrics collection
observer = config.enable_observability()

# Use configuration normally
host = config.database.host

# Get metrics statistics
metrics = config.get_metrics()
print(f"Config accessed {metrics['accessed_keys']} times")
print(f"Reload count: {metrics['reload_count']}")

# Enable event emission
emitter = config.enable_events()

@emitter.on("reload")
def handle_reload(new_config, duration):
    print(f"Config reloaded in {duration}s")

# Or register without decorator
emitter.on("change", lambda old, new: print("Config changed"))
```

#### Advanced Merging Strategies

```python
from config_stash.merge_strategies import AdvancedConfigMerger, MergeStrategy

merger = AdvancedConfigMerger(MergeStrategy.MERGE)
merger.set_strategy("database", MergeStrategy.REPLACE)  # Replace entire section
merger.set_strategy("app.debug", MergeStrategy.REPLACE)  # Replace specific key

result = merger.merge(base_config, override_config)
```

#### Configuration Composition

```yaml
# config/base.yaml
_defaults:
  - database: postgres
  - cache: redis

_include:
  - config/shared.yaml
  - config/features.yaml

app:
  name: MyApp
  version: 1.0.0
```

📖 **See [examples/advanced_features.py](examples/advanced_features.py)**

### 🛠️ Developer Experience

#### Debug Mode & Source Tracking

```python
config = Config(debug_mode=True)

# Find where a value came from
source = config.get_source("database.port")
print(f"database.port loaded from: {source}")

# Get detailed information
info = config.get_source_info("database.port")
print(f"Value: {info.value}")
print(f"Source: {info.source_file}")
print(f"Override count: {info.override_count}")

# Export debug report
config.export_debug_report("config_debug.json")
```

#### IDE Support

```python
# Auto-generates type stubs for IDE autocomplete
config = Config(
    loaders=[YamlLoader("config.yaml")],
    enable_ide_support=True,
    ide_stub_path=".config_stash/stubs.pyi"
)

# Your IDE will now provide autocomplete for config keys!
```

#### ConfigBuilder Pattern

```python
from config_stash import ConfigBuilder
from config_stash.loaders import YamlLoader

config = (ConfigBuilder()
    .with_env("production")
    .add_loader(YamlLoader("config.yaml"))
    .enable_deep_merge()
    .with_schema(AppConfig, validate_on_load=True)
    .build())
```

---

## CLI Tools

> Requires `pip install config-stash[cli]`

Config-Stash includes a CLI for common operations:

```bash
# Validate configuration
config-stash validate production --loader yaml:config.yaml

# Lint configuration for best practices
config-stash lint production --loader yaml:config.yaml

# Export configuration
config-stash export production --format=json --output=config.json

# Show configuration sources
config-stash debug production --key=database.host

# Explain how a configuration value was resolved
config-stash explain production --key=database.host

# Compare two configurations
config-stash diff development production \
    --loader1 yaml:dev.yaml \
    --loader2 yaml:prod.yaml

# Migrate from other tools
config-stash migrate dotenv .env --output config.yaml
config-stash migrate dynaconf settings.yaml --output config.yaml
config-stash migrate hydra conf/config.yaml --output config.yaml

# Load with overrides
config-stash load production \
    --loader yaml:config.yaml \
    --override "database.host=remote.db.example.com" \
    --override "database.port=3306"
```

---

## Examples

We provide comprehensive examples for all major features:

| Example | Description | File |
|---------|-------------|------|
| **Basic Usage** | Getting started with Config-Stash | [examples/basic_usage.py](examples/basic_usage.py) |
| **Introspection API** | Query and explore configuration | [examples/introspection_api.py](examples/introspection_api.py) |
| **Validation** | Schema validation with Pydantic and JSON Schema | [examples/validation_example.py](examples/validation_example.py) |
| **Async Support** | Async/await patterns | [examples/async_example.py](examples/async_example.py) |
| **Secret Stores** | AWS, Azure, GCP, Vault integration | [examples/secret_store_example.py](examples/secret_store_example.py) |
| **Advanced Features** | Versioning, diff, observability, composition | [examples/advanced_features.py](examples/advanced_features.py) |
| **Working Demo** | Complete end-to-end example | [examples/working_demo.py](examples/working_demo.py) |

**Run an example:**
```bash
python examples/basic_usage.py
python examples/introspection_api.py
python examples/async_example.py
```

---

## Documentation

### API Reference

- **[Config Class](src/config_stash/config.py)** - Main configuration class
- **[Loaders](src/config_stash/loaders/)** - Configuration loaders
- **[Secret Stores](src/config_stash/secret_stores/)** - Secret management
- **[Validators](src/config_stash/validators/)** - Schema validation
- **[CLI](src/config_stash/cli.py)** - Command-line interface

### Guides

- **[Secret Stores Guide](docs/SECRET_STORES.md)** - Complete secret store documentation
- **[Vault Authentication](docs/VAULT_AUTHENTICATION.md)** - HashiCorp Vault authentication methods
- **[Migration Guide](docs/MIGRATION_GUIDE.md)** - Migrating from other libraries

---

## Feature Comparison

| Feature | Config-Stash | python-dotenv | Dynaconf | Hydra | OmegaConf | pydantic-settings |
|---------|-------------|---------------|----------|-------|-----------|-------------------|
| **Multiple file formats** | ✅✅ | ❌ | ✅ | ✅ | ✅ | Limited |
| **Source tracking** | ✅✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Cloud storage** | ✅✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Secret stores** | ✅✅ | ❌ | ⚠️ | ❌ | ❌ | ❌ |
| **Schema validation** | ✅ | ❌ | ⚠️ | ✅ | ❌ | ✅✅ |
| **Type safety** | ✅ | ❌ | ❌ | ✅ | ✅ | ✅✅ |
| **Configuration composition** | ✅ | ❌ | ❌ | ✅✅ | ❌ | ❌ |
| **Override system** | ✅✅ | ❌ | ⚠️ | ✅✅ | ✅✅ | ❌ |
| **Introspection API** | ✅✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **Incremental reloading** | ✅✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Async/await support** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Configuration versioning** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Drift detection** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Observability/metrics** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **IDE autocomplete** | ✅ | ❌ | ❌ | ✅ | ✅ | ✅✅ |
| **Hot reload** | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Type casting** | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ |

**Legend:** ✅✅ = Strong/Unique feature, ✅ = Supported, ⚠️ = Partial support, ❌ = Not supported

---

## Testing

```python
import pytest
from config_stash import Config
from config_stash.loaders import YamlLoader

@pytest.fixture
def test_config():
    return Config(loaders=[
        YamlLoader("tests/fixtures/test_config.yaml")
    ])

def test_database_config(test_config):
    assert test_config.database.host == "localhost"
    assert test_config.database.port == 5432
```

Run tests:
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=config_stash

# Run specific test file
pytest tests/test_config.py
```

---

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

```bash
# Clone repository
git clone https://github.com/qatoolist/config-stash.git
cd config-stash

# Install development dependencies
make setup

# Run tests
make test

# Run all checks (lint, type check, tests)
make check
```

---

## License

MIT License. See [LICENSE.txt](LICENSE.txt) for details.

---

## Links

- 📖 **Documentation**: [GitHub Repository](https://github.com/qatoolist/config-stash)
- 📦 **PyPI Package**: [config-stash on PyPI](https://pypi.org/project/config-stash)
- 🐛 **Issue Tracker**: [GitHub Issues](https://github.com/qatoolist/config-stash/issues)
- 📝 **Changelog**: [CHANGELOG.md](CHANGELOG.md)

---

<div align="center">

**Built with ❤️ by [QAToolist](https://github.com/qatoolist) and contributors**

Made for developers who value type safety, observability, and developer experience.

</div>
