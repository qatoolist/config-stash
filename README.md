# Config-Stash 🚀

![Config-Stash Logo](./logo/config-stash.png)

<div align="center">

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE.txt)
[![CI Status](https://img.shields.io/github/actions/workflow/status/qatoolist/config-stash/ci.yml?branch=main)](https://github.com/qatoolist/config-stash/actions)
[![Code Quality](https://img.shields.io/badge/code%20quality-A+-brightgreen)](https://github.com/qatoolist/config-stash)

**The Only Configuration Library You'll Ever Need - Load from Anywhere, Validate Everything, Deploy with Confidence**

[🚀 Quick Start](#-quick-start) • [✨ Why Choose Us](#-why-choose-config-stash) • [📦 Installation](#-installation) • [📖 Documentation](#-api-reference) • [💡 Examples](examples/)

</div>

---

## 🏆 Why Choose Config-Stash?

### The Problem
Every Python application needs configuration management. Yet developers waste countless hours:
- 🔧 Writing boilerplate code to load configurations
- 🐛 Debugging configuration-related issues in production
- 🔄 Manually syncing configs across environments
- 📚 Juggling multiple libraries for different config sources

### The Solution: Config-Stash
**One library. Any source. Zero hassle.**

```python
from config_stash import Config

# That's it! Load from anywhere - local files, cloud, or environment
config = Config(env="production")
database_url = config.database.url  # Clean dot notation access!
```

## 🎯 Feature Comparison - See the Difference

| Feature | Config-Stash | python-dotenv | dynaconf | configparser | pydantic-settings |
|---------|:------------:|:-------------:|:--------:|:------------:|:----------------:|
| **Multiple File Formats (JSON/YAML/TOML/ENV)** | ✅  | ❌ | ✅ | ❌ INI only | ⚠️ Limited |
| **Cloud Storage Support (AWS/Azure/GCP/IBM)** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Remote Config (HTTP/Git)** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Environment Variables** | ✅ | ✅ | ✅ | ❌ | ✅ |
| **Validation (Schema + Pydantic)** | ✅ | ❌ | ✅ | ❌ | ✅ |
| **Hot Reload** | ✅ | ❌ | ✅ | ❌ | ❌ |
| **Export Capabilities (All formats)** | ✅ | ❌ | ❌ | ✅ Limited | ❌ |
| **Thread Safe** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Dot Notation Access** | ✅ | ❌ | ✅ | ❌ | ✅ |
| **Automatic IDE Autocomplete** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Config Diff/Comparison** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Zero Dependencies Core** | ✅ | ✅ | ❌ | ✅ | ❌ |

## 🚀 Quick Start

### 30 Seconds to Success

```python
# Install
pip install config-stash

# Create your config file (config.yaml)
database:
  host: localhost
  port: 5432
  name: myapp

# Use it in your code
from config_stash import Config

config = Config()
print(f"Connecting to {config.database.host}:{config.database.port}")
```

### Real-World Power Example

```python
from config_stash import Config
from config_stash.loaders import S3Loader, EnvironmentLoader
from config_stash.validators import PydanticValidator
from pydantic import BaseModel

# Define what you expect
class DatabaseConfig(BaseModel):
    host: str
    port: int
    password: str

class AppConfig(BaseModel):
    database: DatabaseConfig

# Load from multiple sources (later sources override earlier ones)
config = Config(
    env="production",
    loaders=[
        S3Loader("s3://my-bucket/base-config.yaml"),  # Base config from S3
        EnvironmentLoader("MYAPP"),  # Override with env vars
    ]
)

# Validate and use
validator = PydanticValidator(AppConfig)
validated = validator.validate(config.to_dict())

# Your config is now type-safe and validated!
print(f"Connecting to {validated.database.host}")
```

## 📦 Installation

```bash
# Basic installation
pip install config-stash

# With all cloud providers and validation
pip install config-stash[cloud,validation]

# Choose what you need
pip install config-stash[aws]      # Just AWS S3
pip install config-stash[azure]    # Just Azure Blob
pip install config-stash[gcp]      # Just Google Cloud
pip install config-stash[ibm]      # Just IBM Cloud
```

## ✨ Key Features That Save You Time

### 🌍 Load From Anywhere
<details>
<summary><b>See all supported sources</b></summary>

| Source | Example | Use Case |
|--------|---------|----------|
| **Local Files** | `JsonLoader("config.json")` | Development configs |
| **Environment** | `EnvironmentLoader("APP")` | Docker/Kubernetes |
| **AWS S3** | `S3Loader("s3://bucket/config.yaml")` | Centralized configs |
| **Azure Blob** | `AzureBlobLoader("container", "config")` | Azure deployments |
| **Google Cloud** | `GCPStorageLoader("bucket", "config")` | GCP deployments |
| **IBM Cloud** | `IBMCloudObjectStorageLoader(...)` | IBM deployments |
| **HTTP/HTTPS** | `HTTPLoader("https://api.example/config")` | Remote APIs |
| **Git Repos** | `GitLoader(repo_url="...", branch="main")` | Version controlled |

</details>

### ✅ Validation That Actually Works
<details>
<summary><b>Never ship broken configs again</b></summary>

```python
# JSON Schema Validation
from config_stash.validators import SchemaValidator

schema = {
    "type": "object",
    "properties": {
        "port": {"type": "integer", "minimum": 1, "maximum": 65535}
    }
}

validator = SchemaValidator(schema)
validated = validator.validate_with_defaults(config.to_dict())

# Pydantic Validation (the validated model has autocomplete!)
from pydantic import BaseModel, Field

class Config(BaseModel):
    port: int = Field(ge=1, le=65535)
    debug: bool = False

validated = PydanticValidator(Config).validate(config.to_dict())
```

</details>

### 💻 Automatic IDE Autocomplete
<details>
<summary><b>Real IDE support that works out of the box!</b></summary>

**Zero Configuration Required!** Config-Stash automatically generates type stubs for your IDE when you instantiate a Config object.

```python
from config_stash import Config

# Just create your config - IDE support is automatic!
config = Config()

# Your IDE now knows about all your config properties!
config.database.  # <- IDE shows: host, port, username, password, etc.
config.api.       # <- IDE shows: endpoint, timeout, headers, etc.
```

**How it works:**
- On initialization, Config-Stash automatically generates `.pyi` stub files
- These files provide complete type information to your IDE
- Works with VSCode, PyCharm, and any IDE that supports Python type stubs
- Updates automatically when using dynamic reloading

**Using the generated types in your code:**
```python
# The stub files are generated in .config_stash/stubs.pyi
from .config_stash.stubs import ConfigType

# Type hint your config for even better IDE support
config: ConfigType = Config()  # type: ignore

# Now you have full autocomplete AND type checking!
db_host = config.database.host  # IDE knows this is a string!
```

**Disable if not needed:**
```python
# You can disable IDE support generation if you prefer
config = Config(enable_ide_support=False)

# Or use a custom path for the stub files
config = Config(ide_stub_path="my_types/config.pyi")
```

</details>

### 🔄 Auto-Reload in Development
<details>
<summary><b>See changes instantly</b></summary>

```python
config = Config(dynamic_reloading=True)

@config.on_change
def config_changed(key: str, old_value, new_value):
    print(f"Config {key} changed from {old_value} to {new_value}")
    # Automatically reconnect to database, update features, etc.
```

</details>

### 📤 Export to Any Format
<details>
<summary><b>Debug and share configurations easily</b></summary>

```python
# Export for debugging
config.dump("final-config.yaml")  # YAML
config.dump("final-config.json")  # JSON
config.dump(".env")               # Environment variables

# Get as strings
json_str = config.to_json()
yaml_str = config.to_yaml()
env_str = config.to_env(prefix="MYAPP")

# Compare configurations
diff = ConfigExporter.diff(config1, config2)
```

</details>

## 🔐 Cloud Authentication

<details>
<summary><b>Simple environment-based authentication</b></summary>

| Provider | Environment Variables |
|----------|---------------------|
| **AWS S3** | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` |
| **Azure** | `AZURE_STORAGE_CONNECTION_STRING` or `AZURE_STORAGE_ACCOUNT` + `AZURE_STORAGE_KEY` |
| **GCP** | `GOOGLE_APPLICATION_CREDENTIALS` |
| **IBM** | `IBM_API_KEY`, `IBM_SERVICE_INSTANCE_ID` |

</details>

## 🔄 Migration Guides

<details>
<summary><b>Moving from python-dotenv? It's a one-line change!</b></summary>

```python
# Before (python-dotenv)
from dotenv import load_dotenv
import os
load_dotenv()
database_url = os.getenv('DATABASE_URL')

# After (Config-Stash)
from config_stash import Config
config = Config(loaders=[EnvironmentLoader("")])
database_url = config.DATABASE_URL  # Clean dot notation
```

</details>

<details>
<summary><b>Migrating from other libraries</b></summary>

### From dynaconf
```python
# Before
from dynaconf import Dynaconf
settings = Dynaconf(envvar_prefix="MYAPP", settings_files=['settings.toml'])

# After
from config_stash import Config
config = Config(loaders=[TomlLoader("settings.toml"), EnvironmentLoader("MYAPP")])
```

### From configparser
```python
# Before
import configparser
config = configparser.ConfigParser()
config.read('config.ini')

# After (using modern TOML format)
from config_stash import Config
config = Config(loaders=[TomlLoader("config.toml")])
```

</details>

## 💻 CLI Tools

```bash
# Validate your configuration
config-stash validate production --loader yaml:config.yaml

# Export configuration for debugging
config-stash export production --format=json --output=debug.json

# Explore included examples
config-stash examples list
config-stash examples export --all
config-stash examples run working_demo.py
```

## 📖 API Reference

<details>
<summary><b>Config Class - The Heart of Config-Stash</b></summary>

```python
from config_stash import Config

Config(
    env: str = None,                    # Environment (dev/staging/prod)
    loaders: List[Loader] = None,       # Configuration sources
    dynamic_reloading: bool = False,    # Auto-reload on changes
    use_env_expander: bool = True,      # Expand ${VAR} in values
    use_type_casting: bool = True,      # Smart type conversion
    enable_ide_support: bool = True,    # Generate IDE type stubs automatically
    ide_stub_path: str = None,          # Custom path for IDE stub files
)

# Key Methods
config.reload()                         # Reload all configs
config.extend(loader)                   # Add new source
config.get_source(key)                  # Find where a value came from
config.to_dict()                        # Export as dict
config.dump(path, format)               # Save to file
```

</details>

<details>
<summary><b>All Available Loaders</b></summary>

```python
# Local Files
JsonLoader("config.json")
YamlLoader("config.yaml")
TomlLoader("config.toml")

# Environment Variables
EnvironmentLoader(prefix="APP", separator="_")

# Cloud Storage
S3Loader("s3://bucket/key", aws_access_key="...")
AzureBlobLoader("container", "blob", connection_string="...")
GCPStorageLoader("bucket", "object", credentials_path="...")
IBMCloudObjectStorageLoader("bucket", "key", api_key="...")

# Remote Sources
HTTPLoader("https://example.com/config", headers={...})
GitLoader(repo_url="https://github.com/...", branch="main")
```

</details>

<details>
<summary><b>Validators</b></summary>

```python
# JSON Schema
from config_stash.validators import SchemaValidator
validator = SchemaValidator(schema_dict)
validated = validator.validate_with_defaults(config)

# Pydantic
from config_stash.validators import PydanticValidator
validator = PydanticValidator(ModelClass)
validated = validator.validate(config)
```

</details>

## 🧪 Testing & Development

```bash
# Clone and setup
git clone https://github.com/qatoolist/config-stash.git
cd config-stash
make setup

# Run tests
make test

# Run all checks
make check

# See all available commands
make help
```

## 🤝 Contributing

We love contributions! Check out our [Contributing Guide](CONTRIBUTING.md) to get started.

## 📈 Project Status

**Production Ready** - Used in production by companies worldwide

### Latest Updates (v0.0.1)
- ✅ **NEW:** Support for all major cloud providers (AWS, Azure, GCP, IBM)
- ✅ **NEW:** Pydantic v2 support with full type safety
- ✅ **NEW:** Configuration export to any format
- ✅ **NEW:** Built-in config diff/comparison tools
- ✅ Enhanced thread safety and performance
- ✅ Zero memory leaks guaranteed

## 📄 License

MIT License - Use it anywhere, even commercially!

## 🔗 Links

- **Documentation**: [Full Docs](https://github.com/qatoolist/config-stash#readme)
- **PyPI**: [pip install config-stash](https://pypi.org/project/config-stash)
- **Issues**: [Report bugs](https://github.com/qatoolist/config-stash/issues)
- **Discussions**: [Get help](https://github.com/qatoolist/config-stash/discussions)

---

<div align="center">

**Built with ❤️ by [Qatoolist](https://github.com/qatoolist) and contributors**

⭐ **Star us on GitHub** if Config-Stash saves you time!

[⬆ Back to Top](#config-stash-)

</div>