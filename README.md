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

# With all features
pip install config-stash[all]

# With specific features
pip install config-stash[yaml,toml,s3,validation]
```

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

## ✨ Features

### 🔧 Core Features

<details>
<summary><b>Multi-Format Support</b></summary>

```python
from config_stash import Config
from config_stash.loaders import *

config = Config(
    env="development",
    loaders=[
        JsonLoader("config.json"),
        YamlLoader("config.yaml"),
        TomlLoader("config.toml"),
        EnvironmentLoader("APP"),  # APP_DATABASE_HOST -> database.host
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
| `JsonLoader` | Load from JSON files | `JsonLoader("config.json")` |
| `YamlLoader` | Load from YAML files | `YamlLoader("config.yaml")` |
| `TomlLoader` | Load from TOML files | `TomlLoader("config.toml")` |
| `EnvironmentLoader` | Load from environment variables | `EnvironmentLoader("APP")` |
| `HTTPLoader` | Load from HTTP/HTTPS URLs | `HTTPLoader("https://...")` |
| `S3Loader` | Load from AWS S3 | `S3Loader("s3://...")` |
| `GitLoader` | Load from Git repositories | `GitLoader(repo_url="...")` |

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

## 📈 Project Status

Config-Stash is actively maintained and production-ready. We follow semantic versioning and maintain backward compatibility in minor and patch releases.

### Recent Updates
- ✅ Added remote configuration loading (HTTP, S3, Git)
- ✅ Implemented JSON Schema and Pydantic validation
- ✅ Added comprehensive export functionality
- ✅ Improved thread safety and performance
- ✅ Enhanced documentation and examples

---

<div align="center">

**Made with ❤️ by [Anand Chavan](https://github.com/qatoolist) and contributors**

⭐ Star us on GitHub if you find this project useful!

</div>
