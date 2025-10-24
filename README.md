# Config-Stash 🚀

![Config-Stash Logo](./logo/config-stash.png)

<div align="center">

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE.txt)
[![CI Status](https://img.shields.io/github/actions/workflow/status/qatoolist/config-stash/ci.yml?branch=main)](https://github.com/qatoolist/config-stash/actions)
[![Code Quality](https://img.shields.io/badge/code%20quality-A+-brightgreen)](https://github.com/qatoolist/config-stash)

**A powerful, flexible, and production-ready configuration management library for Python applications**

[Quick Start](#-quick-start) • [Features](#-features) • [Installation](#-installation) • [Documentation](#-documentation) • [Examples](examples/) • [Contributing](CONTRIBUTING.md)

</div>

---

## 🎯 Why Config-Stash?

Config-Stash is designed to solve real-world configuration challenges in modern Python applications:

- **🔄 Multi-Source Configuration**: Seamlessly load from JSON, YAML, TOML, environment variables, remote URLs, S3, and Git repositories
- **✅ Validation First**: Built-in JSON Schema and Pydantic validation ensures your configs are always correct
- **🌍 Environment Management**: Effortlessly handle development, staging, and production configurations
- **📤 Export Anywhere**: Export configurations to any format - perfect for debugging and deployment
- **🔒 Production Ready**: Thread-safe, memory-efficient, with comprehensive error handling
- **🎨 Developer Friendly**: Intuitive API with attribute-style access and excellent IDE support

## 📦 Installation

```bash
# Basic installation
pip install config-stash

# With all features (includes cloud providers and validation)
pip install config-stash[cloud,validation]

# With specific cloud providers
pip install config-stash[cloud]  # All cloud providers
pip install "config-stash[cloud]" # AWS S3 + Azure + GCP + IBM

# Individual cloud providers
pip install "boto3>=1.26.0"  # For AWS S3
pip install "azure-storage-blob>=12.14.0"  # For Azure Blob Storage
pip install "google-cloud-storage>=2.7.0"  # For Google Cloud Storage
pip install "ibm-cos-sdk>=2.13.0"  # For IBM Cloud Object Storage

# With validation features
pip install config-stash[validation]  # Pydantic + JSON Schema validation
```

### 🔐 Environment Variables for Cloud Authentication

Config-Stash cloud loaders support authentication via environment variables:

| Provider | Environment Variables |
|----------|---------------------|
| **AWS S3** | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION` |
| **Azure** | `AZURE_STORAGE_ACCOUNT`, `AZURE_STORAGE_KEY`, `AZURE_SAS_TOKEN`, `AZURE_STORAGE_CONNECTION_STRING` |
| **GCP** | `GCP_PROJECT_ID`, `GOOGLE_APPLICATION_CREDENTIALS` |
| **IBM** | `IBM_API_KEY`, `IBM_SERVICE_INSTANCE_ID` |
| **Git** | `GIT_TOKEN` (for private repositories) |

## 🚀 Quick Start

### Basic Usage - Load Your First Config

```python
from config_stash import Config

# Load from a single file (auto-detects format)
config = Config(env="development")

# Access configuration with dot notation
print(config.database.host)  # "localhost"
print(config.database.port)  # 5432
```

### Real-World Example - Multi-Environment Setup

```python
from config_stash import Config
from config_stash.loaders import JsonLoader, YamlLoader, EnvironmentLoader

# Load from multiple sources with environment-specific overrides
config = Config(
    env="production",
    loaders=[
        YamlLoader("config/base.yaml"),      # Base configuration
        JsonLoader("config/prod.json"),      # Production overrides
        EnvironmentLoader("MYAPP"),          # Environment variables
    ]
)

# Configuration is merged in order - later sources override earlier ones
db_url = f"postgresql://{config.database.username}@{config.database.host}/{config.database.name}"
```

### Advanced Example - Cloud Storage with Validation

```python
from config_stash import Config
from config_stash.loaders import (
    S3Loader, AzureBlobLoader, GCPStorageLoader,
    JsonLoader, EnvironmentLoader
)
from config_stash.validators import PydanticValidator, SchemaValidator
from pydantic import BaseModel, Field

# Define configuration schema using Pydantic
class DatabaseConfig(BaseModel):
    host: str = Field(..., description="Database host")
    port: int = Field(default=5432, ge=1, le=65535)
    username: str
    password: str = None
    ssl_enabled: bool = Field(default=True)

class AppConfig(BaseModel):
    database: DatabaseConfig
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")

# Load configuration from multiple cloud sources
config = Config(
    env="production",
    loaders=[
        # Load base config from AWS S3
        S3Loader(
            "s3://my-configs/base.yaml",
            aws_access_key="YOUR_KEY",
            aws_secret_key="YOUR_SECRET"
        ),

        # Override with Azure-specific settings
        AzureBlobLoader(
            container_url="configs",
            blob_name="prod-overrides.json",
            connection_string="DefaultEndpoints..."
        ),

        # Load secrets from GCP
        GCPStorageLoader(
            bucket_name="my-secrets",
            blob_name="database-creds.yaml",
            project_id="my-project"
        ),

        # Final overrides from environment
        EnvironmentLoader("APP")
    ]
)

# Validate configuration with Pydantic
validator = PydanticValidator(AppConfig)
validated_config = validator.validate(config.to_dict())

# Access validated configuration
print(f"Connecting to {validated_config.database.host}:{validated_config.database.port}")

# Export final configuration for debugging
config.dump("final-config.yaml", format="yaml")

# Watch for changes (if using local files)
@config.on_change
def config_changed(key: str, old_value, new_value):
    print(f"Config changed: {key} = {new_value}")
```

## ✨ Features

### 🔧 Core Features

<details>
<summary><b>Multi-Format & Multi-Cloud Support</b></summary>

```python
from config_stash import Config
from config_stash.loaders import *

config = Config(
    env="development",
    loaders=[
        # Local file formats
        JsonLoader("config.json"),
        YamlLoader("config.yaml"),
        TomlLoader("config.toml"),
        EnvironmentLoader("APP"),

        # Cloud storage providers
        S3Loader("s3://bucket/config.yaml"),              # AWS S3
        AzureBlobLoader("container", "config.json"),      # Azure Blob Storage
        GCPStorageLoader("bucket", "config.toml"),        # Google Cloud Storage
        IBMCloudObjectStorageLoader("bucket", "config"),  # IBM Cloud Object Storage
    ]
)
```
</details>

<details>
<summary><b>Attribute-Style Access</b></summary>

```python
# Instead of dict-style access
host = config["database"]["host"]
port = config["database"]["port"]

# Use intuitive dot notation
host = config.database.host
port = config.database.port

# With IDE autocompletion support!
```
</details>

<details>
<summary><b>Environment-Specific Configurations</b></summary>

```yaml
# config.yaml
development:
  database:
    host: localhost
    port: 5432

production:
  database:
    host: prod-db.example.com
    port: 5432
    ssl: true
```

```python
# Automatically loads the right environment
config = Config(env="production")
assert config.database.ssl == True
```
</details>

### 🛡️ Validation & Type Safety

<details>
<summary><b>JSON Schema Validation</b></summary>

```python
from config_stash.validators import SchemaValidator

schema = {
    "type": "object",
    "properties": {
        "port": {"type": "integer", "minimum": 1, "maximum": 65535},
        "host": {"type": "string", "format": "hostname"}
    },
    "required": ["host", "port"]
}

validator = SchemaValidator(schema)
config_dict = validator.validate_with_defaults({"host": "localhost"})
# port gets default value, host is validated
```
</details>

<details>
<summary><b>Pydantic Model Validation</b></summary>

```python
from pydantic import BaseModel, Field
from config_stash.validators import PydanticValidator

class DatabaseConfig(BaseModel):
    host: str = Field(default="localhost")
    port: int = Field(default=5432, ge=1, le=65535)
    database: str
    username: str
    password: str = Field(default=None)

class AppConfig(BaseModel):
    name: str
    version: str = "1.0.0"
    database: DatabaseConfig

# Validate with type safety
validator = PydanticValidator(AppConfig)
validated_config = validator.validate(config.to_dict())
```
</details>

### 🌐 Remote Configuration Loading

<details>
<summary><b>Load from HTTP/HTTPS</b></summary>

```python
from config_stash.loaders import HTTPLoader

config = Config(
    env="production",
    loaders=[
        HTTPLoader(
            "https://config-server.example.com/app/config.json",
            headers={"Authorization": "Bearer token"},
            timeout=30
        )
    ]
)
```
</details>

<details>
<summary><b>Load from AWS S3</b></summary>

```python
from config_stash.loaders import S3Loader

config = Config(
    env="production",
    loaders=[
        S3Loader(
            "s3://my-bucket/configs/app-config.yaml",
            aws_access_key="YOUR_KEY",
            aws_secret_key="YOUR_SECRET"
        )
    ]
)
```
</details>

<details>
<summary><b>Load from Azure Blob Storage</b></summary>

```python
from config_stash.loaders import AzureBlobLoader

config = Config(
    env="production",
    loaders=[
        AzureBlobLoader(
            container_url="mycontainer",
            blob_name="configs/app-config.yaml",
            account_name="mystorageaccount",
            account_key="YOUR_KEY"  # Or use SAS token/connection string
        )
    ]
)
```
</details>

<details>
<summary><b>Load from Google Cloud Storage</b></summary>

```python
from config_stash.loaders import GCPStorageLoader

config = Config(
    env="production",
    loaders=[
        GCPStorageLoader(
            bucket_name="my-bucket",
            blob_name="configs/app-config.json",
            project_id="my-project",
            credentials_path="/path/to/service-account.json"
        )
    ]
)
```
</details>

<details>
<summary><b>Load from IBM Cloud Object Storage</b></summary>

```python
from config_stash.loaders import IBMCloudObjectStorageLoader

config = Config(
    env="production",
    loaders=[
        IBMCloudObjectStorageLoader(
            bucket_name="my-bucket",
            object_key="configs/app-config.toml",
            api_key="YOUR_API_KEY",
            service_instance_id="YOUR_INSTANCE_ID",
            region="us-south"
        )
    ]
)
```
</details>

<details>
<summary><b>Load from Git Repositories</b></summary>

```python
from config_stash.loaders import GitLoader

config = Config(
    env="production",
    loaders=[
        GitLoader(
            repo_url="https://github.com/myorg/config",
            file_path="configs/production.yaml",
            branch="main",
            token="github_token"  # For private repos
        )
    ]
)
```
</details>

### 📤 Export & Conversion

<details>
<summary><b>Export to Multiple Formats</b></summary>

```python
from config_stash.exporters import add_export_methods

# Add export methods to Config class
add_export_methods(Config)

# Export to different formats
config.dump("config.json")      # Auto-detects format from extension
config.dump("config.yaml")
config.dump("config.toml")
config.dump(".env", format="env")  # Export as environment variables

# Or get as strings
json_str = config.to_json(indent=2)
yaml_str = config.to_yaml()
env_str = config.to_env(prefix="MYAPP")
```
</details>

<details>
<summary><b>Configuration Diff</b></summary>

```python
from config_stash.exporters import ConfigExporter

# Compare two configurations
diff = ConfigExporter.diff(config1, config2, format="json")
print(diff)
# {
#   "+ new_key": "added_value",
#   "- removed_key": "old_value",
#   "~ modified_key": {"old": "value1", "new": "value2"}
# }
```
</details>

### 🔄 Advanced Features

<details>
<summary><b>Dynamic Configuration Reloading</b></summary>

```python
# Auto-reload when files change
config = Config(
    env="development",
    loaders=[YamlLoader("config.yaml")],
    dynamic_reloading=True
)

# Config automatically updates when config.yaml is modified
# Stop watching when done
config.stop_watching()
```
</details>

<details>
<summary><b>Configuration Hooks & Transformations</b></summary>

```python
config = Config(env="development")

# Register transformation hooks
config.hook_processor.register_value_hook(
    lambda x: x.upper() if isinstance(x, str) else x
)

# Register conditional hooks
config.hook_processor.register_condition_hook(
    lambda k, v: v * 2 if k == "timeout" else v
)
```
</details>

<details>
<summary><b>Configuration Extension</b></summary>

```python
# Start with base config
config = Config(env="development")

# Extend with additional configurations
config.extend(JsonLoader("extra_config.json"))
config.extend(YamlLoader("overrides.yaml"))

# Or extend with dict
config.extend({"new_feature": {"enabled": True}})
```
</details>

## 📚 Documentation

### Configuration File Examples

<details>
<summary><b>YAML Configuration</b></summary>

```yaml
# config.yaml
default:
  app:
    name: MyApplication
    version: 1.0.0

  database:
    host: localhost
    port: 5432
    pool:
      min_size: 10
      max_size: 100

development:
  app:
    debug: true
  database:
    host: dev-db.local

production:
  app:
    debug: false
  database:
    host: prod-db.example.com
    ssl:
      enabled: true
      verify: true
```
</details>

<details>
<summary><b>JSON Configuration</b></summary>

```json
{
  "default": {
    "app": {
      "name": "MyApplication",
      "version": "1.0.0"
    },
    "logging": {
      "level": "INFO",
      "format": "json"
    }
  },
  "production": {
    "logging": {
      "level": "WARNING"
    }
  }
}
```
</details>

<details>
<summary><b>TOML Configuration</b></summary>

```toml
[default]
[default.server]
host = "0.0.0.0"
port = 8000
workers = 4

[production.server]
host = "0.0.0.0"
port = 443
workers = 16
ssl_enabled = true
```
</details>

### API Reference

#### Core Classes

| Class | Description |
|-------|-------------|
| `Config` | Main configuration manager |
| `ConfigLoader` | Base loader for configuration sources |
| `SchemaValidator` | JSON Schema validation |
| `PydanticValidator` | Pydantic model validation |
| `ConfigExporter` | Export configurations to various formats |

#### Available Loaders

| Loader | Purpose | Example |
|--------|---------|---------|
| **Local File Loaders** | | |
| `JsonLoader` | Load from JSON files | `JsonLoader("config.json")` |
| `YamlLoader` | Load from YAML files | `YamlLoader("config.yaml")` |
| `TomlLoader` | Load from TOML files | `TomlLoader("config.toml")` |
| `EnvironmentLoader` | Load from environment variables | `EnvironmentLoader("APP")` |
| **Remote Loaders** | | |
| `HTTPLoader` | Load from HTTP/HTTPS URLs | `HTTPLoader("https://api.example.com/config")` |
| `GitLoader` | Load from Git repositories | `GitLoader(repo_url="https://github.com/...")` |
| **Cloud Storage Loaders** | | |
| `S3Loader` | AWS S3 | `S3Loader("s3://bucket/config.yaml")` |
| `AzureBlobLoader` | Azure Blob Storage | `AzureBlobLoader("container", "config.json")` |
| `GCPStorageLoader` | Google Cloud Storage | `GCPStorageLoader("bucket", "config.toml")` |
| `IBMCloudObjectStorageLoader` | IBM Cloud Object Storage | `IBMCloudObjectStorageLoader("bucket", "config")` |

#### Methods

<details>
<summary><b>Config Class Methods</b></summary>

```python
# Initialize
config = Config(env="development", loaders=[...])

# Access configuration
value = config.database.host

# Get source of a configuration key
source = config.get_source("database.host")  # "config.yaml"

# Reload configuration
config.reload()

# Extend configuration
config.extend(new_loader)

# Export (after adding export methods)
config.to_json()
config.to_yaml()
config.to_dict()
config.dump("output.json")
```
</details>

## 💻 CLI Commands

### Configuration Management

```bash
# Load and display configuration
config-stash load <environment> --loader yaml:config.yaml --loader json:config.json

# Get specific configuration value
config-stash get <environment> <key> --loader yaml:config.yaml

# Enable dynamic reloading
config-stash load development --loader yaml:config.yaml --dynamic-reloading
```

### Examples Management

Config-Stash includes a powerful examples management system to help you get started quickly:

```bash
# List all available examples
config-stash examples list
config-stash examples list --verbose  # Show detailed information

# Export examples to your project
config-stash examples export working_demo.py  # Export specific example
config-stash examples export --all            # Export all examples
config-stash examples export working_demo.py --output-dir ./my_examples

# View example source code
config-stash examples show working_demo.py
config-stash examples show working_demo.py --no-pager  # Without pager

# Run examples directly
config-stash examples run working_demo.py
```

### Available Examples

- **working_demo.py** - Comprehensive demo of core features (environments, export, diff)
- **advanced_features.py** - Advanced features including validation and remote loading

## 📖 Complete API Reference

### Core Classes

<details>
<summary><b>Config Class</b></summary>

```python
from config_stash import Config

# Constructor
Config(
    env: str = None,                    # Environment name (development, production, etc.)
    loaders: List[Loader] = None,       # List of configuration loaders
    dynamic_reloading: bool = False,    # Enable file watching for auto-reload
    use_env_expander: bool = True,      # Enable ${VAR} expansion in values
    use_type_casting: bool = True,      # Enable automatic type casting
)

# Properties
config.env_config    # Current environment configuration
config.merged_config # All configurations merged
config.loaders       # List of active loaders

# Methods
config.reload()                      # Reload all configurations
config.extend(loader)                # Add additional loader
config.get_source(key: str)          # Get source file for a key
config.to_dict()                     # Export as dictionary
config.to_json(indent=2)             # Export as JSON string
config.to_yaml()                     # Export as YAML string
config.to_toml()                     # Export as TOML string
config.to_env(prefix="", sep="_")   # Export as environment variables
config.dump(file_path, format=None)  # Save to file

# Decorators
@config.on_change                    # Watch for configuration changes
def handler(key, old_value, new_value): pass
```
</details>

<details>
<summary><b>Loader Classes</b></summary>

```python
# Local File Loaders
from config_stash.loaders import JsonLoader, YamlLoader, TomlLoader

JsonLoader(source: str)              # Load from JSON file
YamlLoader(source: str)              # Load from YAML file
TomlLoader(source: str)              # Load from TOML file

# Environment Loader
from config_stash.loaders import EnvironmentLoader

EnvironmentLoader(
    prefix: str,                     # Environment variable prefix
    separator: str = "_",            # Nested key separator
    lowercase_keys: bool = False,   # Convert keys to lowercase
    type_casting: bool = True,      # Auto-cast types
)

# HTTP Loader
from config_stash.loaders import HTTPLoader

HTTPLoader(
    url: str,                        # HTTP/HTTPS URL
    timeout: int = 30,               # Request timeout in seconds
    headers: Dict = None,            # Optional HTTP headers
    auth: Tuple = None,              # Optional (username, password)
)

# Cloud Storage Loaders
from config_stash.loaders import (
    S3Loader, AzureBlobLoader,
    GCPStorageLoader, IBMCloudObjectStorageLoader
)

S3Loader(
    s3_url: str,                     # s3://bucket/path/to/file
    aws_access_key: str = None,      # AWS access key
    aws_secret_key: str = None,      # AWS secret key
    region: str = "us-east-1",       # AWS region
)

AzureBlobLoader(
    container_url: str,              # Container name or URL
    blob_name: str,                  # Blob (file) name
    account_name: str = None,        # Storage account name
    account_key: str = None,         # Storage account key
    sas_token: str = None,           # SAS token
    connection_string: str = None,   # Full connection string
)

GCPStorageLoader(
    bucket_name: str,                # GCS bucket name
    blob_name: str,                  # Object name
    project_id: str = None,          # GCP project ID
    credentials_path: str = None,    # Service account JSON path
)

IBMCloudObjectStorageLoader(
    bucket_name: str,                # IBM COS bucket
    object_key: str,                 # Object key
    api_key: str = None,             # IBM Cloud API key
    service_instance_id: str = None, # Service instance ID
    endpoint_url: str = None,        # Custom endpoint
    region: str = "us-south",        # IBM Cloud region
)

# Git Loader
from config_stash.loaders import GitLoader

GitLoader(
    repo_url: str,                   # Git repository URL
    file_path: str,                  # Path to config in repo
    branch: str = "main",            # Git branch
    token: str = None,               # Access token for private repos
)
```
</details>

<details>
<summary><b>Validator Classes</b></summary>

```python
# JSON Schema Validator
from config_stash.validators import SchemaValidator

validator = SchemaValidator(
    schema: Dict,                    # JSON Schema dictionary
)

validator.validate(config: Dict)    # Validate configuration
validator.validate_with_defaults(   # Validate with defaults
    config: Dict
) -> Dict

# Pydantic Validator
from config_stash.validators import PydanticValidator

validator = PydanticValidator(
    model_class: Type[BaseModel],   # Pydantic model class
)

validator.validate(config: Dict)    # Returns validated model
validator.validate_to_dict(         # Returns validated dict
    config: Dict
) -> Dict
```
</details>

<details>
<summary><b>Exporter Class</b></summary>

```python
from config_stash.exporters import ConfigExporter

# Static methods
ConfigExporter.to_dict(config)      # Export as dictionary
ConfigExporter.to_json(config,      # Export as JSON
    indent: int = 2
) -> str
ConfigExporter.to_yaml(config,      # Export as YAML
    default_flow_style: bool = False
) -> str
ConfigExporter.to_toml(config)      # Export as TOML
ConfigExporter.to_env(config,       # Export as env vars
    prefix: str = "",
    separator: str = "_"
) -> str
ConfigExporter.dump(config,         # Save to file
    file_path: str,
    format: str = None               # Auto-detect if None
)
ConfigExporter.diff(                # Compare configs
    config1, config2,
    format: str = "json"
) -> str

# Add export methods to Config class
from config_stash.exporters import add_export_methods
add_export_methods(Config)
```
</details>

## 🧪 Testing

```bash
# Run tests
make test

# Run with coverage
make test-coverage

# Run specific test file
pytest tests/test_config.py -v
```

## 🛠️ Development

### Setting Up Development Environment

```bash
# Clone the repository
git clone https://github.com/qatoolist/config-stash.git
cd config-stash

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Available Make Commands

```bash
make help          # Show all available commands
make test          # Run tests
make lint          # Run linters
make format        # Format code
make docs          # Build documentation
make build         # Build distribution packages
make clean         # Clean build artifacts
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### How to Contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE.txt) file for details.

## 🙏 Acknowledgments

- Thanks to the Python community for their valuable feedback and contributions
- Special thanks to all [contributors](https://github.com/qatoolist/config-stash/graphs/contributors)
- Inspired by various configuration management libraries in the Python ecosystem

## 🔗 Links

- **Documentation**: [Config-Stash Docs](https://github.com/qatoolist/config-stash#readme)
- **PyPI Package**: [pypi.org/project/config-stash](https://pypi.org/project/config-stash)
- **Issue Tracker**: [GitHub Issues](https://github.com/qatoolist/config-stash/issues)
- **Discussions**: [GitHub Discussions](https://github.com/qatoolist/config-stash/discussions)
- **Source Code**: [GitHub Repository](https://github.com/qatoolist/config-stash)

## 🔄 Migration Guide

### Migrating from python-dotenv

```python
# python-dotenv
from dotenv import load_dotenv
import os
load_dotenv()
database_url = os.getenv('DATABASE_URL')

# Config-Stash
from config_stash import Config
from config_stash.loaders import EnvironmentLoader

config = Config(loaders=[EnvironmentLoader("")])
database_url = config.DATABASE_URL
```

### Migrating from dynaconf

```python
# dynaconf
from dynaconf import Dynaconf
settings = Dynaconf(
    envvar_prefix="MYAPP",
    settings_files=['settings.toml', 'settings.yaml'],
)

# Config-Stash
from config_stash import Config
from config_stash.loaders import TomlLoader, YamlLoader, EnvironmentLoader

config = Config(
    env="development",
    loaders=[
        TomlLoader("settings.toml"),
        YamlLoader("settings.yaml"),
        EnvironmentLoader("MYAPP")
    ]
)
```

### Migrating from configparser

```python
# configparser
import configparser
config = configparser.ConfigParser()
config.read('config.ini')
database_host = config['database']['host']

# Config-Stash (using TOML instead of INI)
from config_stash import Config
from config_stash.loaders import TomlLoader

config = Config(loaders=[TomlLoader("config.toml")])
database_host = config.database.host
```

### Feature Comparison

| Feature | Config-Stash | python-dotenv | dynaconf | configparser |
|---------|-------------|---------------|----------|--------------|
| Multiple file formats | ✅ | ❌ | ✅ | ❌ |
| Cloud storage support | ✅ | ❌ | ❌ | ❌ |
| Environment variables | ✅ | ✅ | ✅ | ❌ |
| Validation | ✅ | ❌ | ✅ | ❌ |
| Type casting | ✅ | ❌ | ✅ | ✅ |
| Hot reload | ✅ | ❌ | ✅ | ❌ |
| Export capabilities | ✅ | ❌ | ❌ | ✅ |
| Thread safe | ✅ | ✅ | ✅ | ✅ |
| Attribute access | ✅ | ❌ | ✅ | ❌ |
| Remote loading | ✅ | ❌ | ❌ | ❌ |

## 📈 Project Status

Config-Stash is actively maintained and production-ready. We follow semantic versioning and maintain backward compatibility in minor and patch releases.

### Recent Updates
- ✅ **NEW:** Added support for all major cloud storage providers (AWS S3, Azure Blob, GCP Storage, IBM COS)
- ✅ **NEW:** Comprehensive validation with JSON Schema and Pydantic v2 support
- ✅ **NEW:** Full configuration export capabilities (JSON, YAML, TOML, ENV)
- ✅ **NEW:** CLI commands for examples management
- ✅ Added remote configuration loading (HTTP, Git repositories)
- ✅ Improved thread safety with proper locking mechanisms
- ✅ Fixed memory leaks in caching system
- ✅ Enhanced type hints and mypy compliance

---

<div align="center">

**Made with ❤️ by [Anand Chavan](https://github.com/qatoolist) and contributors**

⭐ Star us on GitHub if you find this project useful!

</div>
