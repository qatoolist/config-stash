# Config-Stash

![Config-Stash Logo](./logo/config-stash.png)

<div align="center">

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE.txt)
[![CI Status](https://img.shields.io/github/actions/workflow/status/qatoolist/config-stash/ci.yml?branch=main)](https://github.com/qatoolist/config-stash/actions)
[![PyPI Version](https://img.shields.io/pypi/v/config-stash)](https://pypi.org/project/config-stash/)

**A comprehensive configuration management library for Python applications**

[Installation](#installation) • [Quick Start](#quick-start) • [Features](#features) • [Documentation](#documentation) • [Examples](examples/)

</div>

## Overview

Config-Stash is a flexible configuration management library that simplifies loading, merging, and accessing configuration from multiple sources. It provides a unified interface for managing application settings across different environments with built-in validation, type safety, and debugging capabilities.

## Installation

```bash
pip install config-stash

# Optional dependencies
pip install config-stash[validation]    # Schema validation
pip install config-stash[cloud]         # Cloud storage support
pip install config-stash[secrets]       # Secret store support (AWS, Azure, GCP, Vault)
pip install config-stash[all]           # All features

# Individual secret store dependencies
pip install boto3                        # AWS Secrets Manager
pip install hvac                         # HashiCorp Vault
pip install azure-keyvault-secrets azure-identity  # Azure Key Vault
pip install google-cloud-secret-manager  # GCP Secret Manager
```

## Quick Start

```python
from config_stash import Config

# Basic usage - auto-detects configuration files
config = Config()
print(config.database.host)
print(config.api.timeout)

# Multiple sources with environment-specific overrides
from config_stash.loaders import YamlLoader, EnvironmentLoader

config = Config(
    env="production",
    loaders=[
        YamlLoader("config/base.yaml"),
        YamlLoader("config/production.yaml"),
        EnvironmentLoader("APP"),  # APP_* environment variables
    ]
)

# With secret store integration (NEW!)
from config_stash.secret_stores import AWSSecretsManager, SecretResolver

secret_store = AWSSecretsManager(region_name='us-east-1')
config = Config(
    env="production",
    loaders=[YamlLoader("config.yaml")],
    secret_resolver=SecretResolver(secret_store)
)
# Secrets in config.yaml like "${secret:db/password}" are automatically resolved

# Enable debug mode to track configuration sources
config = Config(debug_mode=True)
print(config.get_source("database.host"))  # Shows: 'config/base.yaml'
```

## Features

### Multiple Configuration Sources

- **Files**: JSON, YAML, TOML, INI, .env
- **Cloud Storage**: AWS S3, Azure Blob Storage, Google Cloud Storage, IBM Cloud Object Storage
- **Remote**: HTTP/HTTPS endpoints, Git repositories
- **Environment Variables**: System environment with prefix support
- **Secret Stores**: AWS Secrets Manager, HashiCorp Vault, Azure Key Vault, GCP Secret Manager
- **Custom Loaders**: Extensible loader interface

### Secret Store Integration 🔐

**NEW!** Config-Stash now includes comprehensive secret store integration for secure credential management:

```python
from config_stash import Config
from config_stash.secret_stores import AWSSecretsManager, SecretResolver
from config_stash.loaders import YamlLoader

# Initialize secret store
secret_store = AWSSecretsManager(region_name='us-east-1')

# Use with Config
config = Config(
    env='production',
    loaders=[YamlLoader('config.yaml')],
    secret_resolver=SecretResolver(secret_store)
)

# Secrets automatically resolved from ${secret:key} placeholders
print(config.database.password)  # Resolved from AWS Secrets Manager
```

**Supported Secret Stores:**
- **AWS Secrets Manager** - AWS native secret management
- **HashiCorp Vault** - Enterprise secret management with 10+ auth methods:
  - ✅ **OIDC with Kerberos** (SSO, no browser if `kinit` done)
  - ✅ **LDAP with PIN+Token** (complex password policies)
  - ✅ JWT, Kubernetes, AWS, Azure, GCP, AppRole, Token
- **Azure Key Vault** - Azure native secret management
- **GCP Secret Manager** - Google Cloud secret management
- **Environment Variables** - Simple env-based secrets
- **DictSecretStore** - In-memory secrets for development/testing
- **MultiSecretStore** - Combine multiple stores with fallback hierarchy
- **Custom Stores** - Extensible secret store interface

**Configuration File with Secret Placeholders:**
```yaml
production:
  database:
    host: prod-db.example.com
    password: "${secret:prod/database/password}"
  api:
    key: "${secret:prod/api/key}"
    endpoint: "https://api.example.com"
```

**Advanced HashiCorp Vault Authentication:**
```python
from config_stash.secret_stores import HashiCorpVault
from config_stash.secret_stores.vault_auth import OIDCAuth, LDAPAuth
import getpass
import os

# OIDC with Kerberos (automatic if kinit done)
auth = OIDCAuth(role='myapp-role', use_kerberos=True)

# Or LDAP with PIN+Token for complex password policies
def get_pin_token():
    pin = getpass.getpass("PIN: ")
    token = getpass.getpass("Token: ")
    return pin + token

auth = LDAPAuth(
    username=os.getenv('USER'),  # Kerberos ID
    password_provider=get_pin_token
)

vault = HashiCorpVault(
    url='https://vault.example.com',
    auth_method=auth
)

config = Config(secret_resolver=SecretResolver(vault))
```

**Multi-Store Fallback:**
```python
from config_stash.secret_stores import MultiSecretStore, DictSecretStore, EnvSecretStore

# Create fallback hierarchy
multi_store = MultiSecretStore([
    DictSecretStore({"override/key": "local-value"}),  # Highest priority
    AWSSecretsManager(region_name='us-east-1'),        # Production secrets
    EnvSecretStore(transform_key=True),                 # Environment fallback
])

config = Config(secret_resolver=SecretResolver(multi_store))
```

**Features:**
- 🔐 Secure credential management
- 🔄 Automatic secret resolution with `${secret:key}` syntax
- 🎯 JSON path extraction for nested secrets: `${secret:key:path.to.value}`
- 💾 Optional caching for performance
- 🔁 Version support for secret rotation
- 🌐 Multi-cloud support (AWS, Azure, GCP)
- 🏢 Enterprise authentication (Kerberos, LDAP, OIDC)
- 🔌 Extensible plugin architecture

📖 **See [Secret Store Documentation](docs/SECRET_STORES.md) and [Vault Authentication Guide](docs/VAULT_AUTHENTICATION.md)** for complete details.

### Source Tracking & Debugging

Config-Stash provides comprehensive debugging capabilities to track configuration sources and overrides:

```python
config = Config(debug_mode=True)

# Find where a value came from
source = config.get_source("database.port")
print(f"database.port loaded from: {source}")

# Get detailed information about a configuration value
info = config.get_source_info("database.port")
if info:
    print(f"Value: {info.value}")
    print(f"Source: {info.source_file}")
    print(f"Override count: {info.override_count}")

# See all overridden values
conflicts = config.get_conflicts()
for key, history in conflicts.items():
    print(f"{key} was overridden {len(history)} times")

# Export full debug report
config.export_debug_report("config_debug.json")
```

### Validation & Type Safety

```python
from config_stash.validators import PydanticValidator
from pydantic import BaseModel, Field

class DatabaseConfig(BaseModel):
    host: str
    port: int = Field(ge=1, le=65535)
    password: str

class AppConfig(BaseModel):
    database: DatabaseConfig

# Validate configuration
validator = PydanticValidator(AppConfig)
validated = validator.validate(config.to_dict())
```

### IDE Support

Config-Stash automatically generates type stubs for IDE autocomplete:

```python
config = Config()  # IDE knows about all your configuration structure
config.database.  # Autocomplete shows available keys
```

### Dynamic Reloading

```python
config = Config(dynamic_reloading=True)

@config.on_change
def handle_config_change(key: str, old_value, new_value):
    print(f"Config {key} changed from {old_value} to {new_value}")
```

### Export & Comparison

```python
# Export configuration
config.dump("config_dump.yaml")
config.dump("config_dump.json")
config.dump(".env", prefix="APP")

# Compare configurations
from config_stash.exporters import ConfigExporter
diff = ConfigExporter.diff(config1, config2, format="yaml")
print(diff)
```

## Documentation

### Configuration Class

```python
from config_stash import Config

Config(
    env: str = None,                    # Environment name
    loaders: List[Loader] = None,       # Configuration sources
    dynamic_reloading: bool = False,    # Auto-reload on file changes
    use_env_expander: bool = True,      # Expand ${VAR} references
    use_type_casting: bool = True,      # Automatic type conversion
    enable_ide_support: bool = True,    # Generate IDE type stubs
    debug_mode: bool = False,           # Enable source tracking
    secret_resolver: SecretResolver = None,  # Secret store integration (NEW!)
)
```

### Available Loaders

```python
# File loaders
from config_stash.loaders import JsonLoader, YamlLoader, TomlLoader
loader = YamlLoader("config.yaml")

# Cloud storage loaders
from config_stash.loaders import S3Loader, AzureBlobLoader, GCPStorageLoader
loader = S3Loader("s3://bucket/config.yaml")

# Remote loaders
from config_stash.loaders import HTTPLoader, GitLoader
loader = HTTPLoader("https://api.example.com/config")

# Environment loader
from config_stash.loaders import EnvironmentLoader
loader = EnvironmentLoader(prefix="APP", separator="_")
```

### Validators

```python
# JSON Schema validation
from config_stash.validators import SchemaValidator
validator = SchemaValidator(schema_dict)

# Pydantic validation
from config_stash.validators import PydanticValidator
validator = PydanticValidator(ModelClass)
```

### Secret Stores

```python
# AWS Secrets Manager
from config_stash.secret_stores import AWSSecretsManager, SecretResolver
store = AWSSecretsManager(region_name='us-east-1')
config = Config(secret_resolver=SecretResolver(store))

# HashiCorp Vault with token auth
from config_stash.secret_stores import HashiCorpVault
store = HashiCorpVault(url='https://vault.example.com', token='s.xxxxx')

# HashiCorp Vault with OIDC + Kerberos
from config_stash.secret_stores.vault_auth import OIDCAuth
auth = OIDCAuth(role='myapp-role', use_kerberos=True)
store = HashiCorpVault(url='https://vault.example.com', auth_method=auth)

# HashiCorp Vault with LDAP + PIN+Token
from config_stash.secret_stores.vault_auth import LDAPAuth
def get_pin_token():
    pin = getpass.getpass("PIN: ")
    token = getpass.getpass("Token: ")
    return pin + token
auth = LDAPAuth(username=os.getenv('USER'), password_provider=get_pin_token)
store = HashiCorpVault(url='https://vault.example.com', auth_method=auth)

# Azure Key Vault
from config_stash.secret_stores import AzureKeyVault
store = AzureKeyVault(vault_url='https://myvault.vault.azure.net')

# GCP Secret Manager
from config_stash.secret_stores import GCPSecretManager
store = GCPSecretManager(project_id='my-project')

# Multi-store with fallback
from config_stash.secret_stores import MultiSecretStore, DictSecretStore
store = MultiSecretStore([
    DictSecretStore({"local/key": "override"}),  # Highest priority
    AWSSecretsManager(region_name='us-east-1'),  # Production
    EnvSecretStore(),                             # Environment fallback
])

# See docs/SECRET_STORES.md for complete documentation
```

## Advanced Usage

### Environment-Specific Configuration

```python
# config/base.yaml
database:
  host: localhost
  port: 5432

# config/production.yaml
database:
  host: prod.db.example.com
  ssl: true

# Usage
config = Config(
    env="production",
    loaders=[
        YamlLoader("config/base.yaml"),
        YamlLoader("config/production.yaml"),
    ]
)
```

### Cloud Configuration

```python
# AWS S3
config = Config(loaders=[
    S3Loader("s3://my-bucket/config.yaml",
             aws_access_key_id=AWS_KEY,
             aws_secret_access_key=AWS_SECRET)
])

# Azure Blob Storage
config = Config(loaders=[
    AzureBlobLoader("container", "config.yaml",
                    connection_string=AZURE_CONNECTION)
])

# Google Cloud Storage
config = Config(loaders=[
    GCPStorageLoader("bucket", "config.yaml",
                     credentials_path="service-account.json")
])
```

### Custom Hooks

```python
config = Config()

# Register transformation hooks
@config.register_key_hook("database.password")
def decrypt_password(value):
    return decrypt(value)

@config.register_condition_hook
def transform_urls(key, value):
    if key.endswith("_url"):
        return value.replace("http://", "https://")
    return value
```

## CLI Tools

```bash
# Validate configuration
config-stash validate production --loader yaml:config.yaml

# Export configuration
config-stash export production --format=json --output=config.json

# Show configuration sources
config-stash debug production --key=database.host
```

## Comparison with Other Libraries

| Feature | Config-Stash | python-dotenv | dynaconf | configparser | pydantic-settings |
|---------|-------------|---------------|----------|--------------|-------------------|
| Multiple file formats | ✅ | ❌ | ✅ | ❌ | Limited |
| Source tracking | ✅ | ❌ | ❌ | ❌ | ❌ |
| Cloud storage | ✅ | ❌ | ❌ | ❌ | ❌ |
| Secret stores | ✅ | ❌ | ❌ | ❌ | ❌ |
| Validation | ✅ | ❌ | ✅ | ❌ | ✅ |
| IDE autocomplete | ✅ | ❌ | ❌ | ❌ | ❌ |
| Hot reload | ✅ | ❌ | ✅ | ❌ | ❌ |
| Type casting | ✅ | ❌ | ✅ | ❌ | ✅ |

## Testing

```python
import pytest
from config_stash import Config

@pytest.fixture
def test_config():
    return Config(loaders=[
        YamlLoader("tests/fixtures/test_config.yaml")
    ])

def test_database_config(test_config):
    assert test_config.database.host == "localhost"
    assert test_config.database.port == 5432
```

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

# Run all checks
make check
```

## License

MIT License. See [LICENSE](LICENSE.txt) for details.

## Links

- [Documentation](https://github.com/qatoolist/config-stash#readme)
- [PyPI Package](https://pypi.org/project/config-stash)
- [Issue Tracker](https://github.com/qatoolist/config-stash/issues)
- [Changelog](CHANGELOG.md)

---

Built with ❤️ by [QAToolist](https://github.com/qatoolist) and contributors
