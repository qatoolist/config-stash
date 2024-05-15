# Config-Stash

![Config-Stash Logo](./logo/config-stash.png)

Config-Stash is a lightweight and extensible Python configuration manager. It supports loading configurations from various formats including YAML, JSON, TOML, and environment variables, with features like environment-specific settings, dynamic merging, attribute-style access, and a robust plugin system. Config-Stash also includes a CLI tool for easy configuration management.

## Key Features

- **Multi-Source Loading**: Load configurations from YAML, JSON, TOML files, and environment variables.
- **Environment-Specific Configurations**: Easily manage environment-specific settings.
- **Attribute Access**: Access configuration values as class attributes for intuitive usage.
- **Dynamic Merging**: Automatically merge configurations from different sources, with support for nested structures.
- **Plugin System**: Extend functionality by adding custom loaders and processors through a robust plugin system.
- **Dynamic Reloading**: Optionally watch configuration files for changes and reload them automatically.
- **Configuration Extending**: Extend the existing configuration by adding or updating key/values dynamically.
- **CLI Tool**: Manage configurations effortlessly via a command-line interface.

## Installation

You can install Config-Stash using pip:

```sh
pip install config-stash
```

## Usage

### Loading Configurations

You can load configurations from multiple sources and access them using attribute-style access.

```python
from config_stash.config import Config
from config_stash.loaders.yaml_loader import YamlLoader
from config_stash.loaders.json_loader import JsonLoader
from config_stash.loaders.toml_loader import TomlLoader
from config_stash.loaders.environment_loader import EnvironmentLoader

loaders = [
    YamlLoader('config.yaml'),
    JsonLoader('config.json'),
    TomlLoader('config.toml'),
    EnvironmentLoader('PREFIX')
]

config = Config(env='stage', loaders=loaders, dynamic_reloading=True)

print(config.some_env.name.isa)
```

### Extending Configurations

You can dynamically extend the existing configuration by adding or updating key/values.

```python
additional_loader = YamlLoader('additional_config.yaml')
config.extend_config(additional_loader)

print(config.some_new_key)
```

### CLI Tool

Config-Stash includes a CLI tool for managing configurations.

```sh
config-stash load stage --loader yaml:config.yaml --loader json:config.json --loader toml:config.toml --loader env:PREFIX --dynamic-reloading
config-stash source stage some_env.name.isa --loader yaml:config.yaml --loader json:config.json --loader toml:config.toml --loader env:PREFIX --dynamic-reloading
```

### Plugin System

Config-Stash allows you to extend its functionality by adding custom loaders and processors via plugins. To add a custom loader, define it and specify it in your `pyproject.toml`.

#### Example Custom Loader

```python
# my_custom_loader.py

from config_stash.loaders.loader import Loader

class MyCustomLoader(Loader):
    def load(self):
        # Custom loading logic
        self.config = {"custom_key": "custom_value"}
        return self.config
```

#### Define Entry Points in `pyproject.toml`

```toml
[tool.config_stash]
default_environment = "development"
default_files = ["config.yaml", "config.json", "config.toml"]
default_prefix = "PREFIX"
dynamic_reloading = false

[tool.config_stash.loaders]
yaml = "config_stash.loaders.yaml_loader:YamlLoader"
json = "config_stash.loaders.json_loader:JsonLoader"
toml = "config_stash.loaders.toml_loader:TomlLoader"
env = "config_stash.loaders.environment_loader:EnvironmentLoader"
my_custom_loader = "my_custom_loader:MyCustomLoader"
```

### Dynamic Reloading

Config-Stash can be configured to watch configuration files and automatically reload them when changes are detected.

```python
config = Config(env='stage', loaders=loaders, dynamic_reloading=True)
# Modify configuration files and observe the changes

# To stop watching files
config.stop_watching()
```

## Contributing

We welcome contributions! Please see our [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to contribute.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE.txt) file for details.

## Authors

- Anand Chavan - [GitHub](https://github.com/qatoolist)

## Acknowledgments

- Thanks to the Python community for their valuable feedback and contributions.

## Project Links

- **Documentation**: [Config-Stash Documentation](https://github.com/qatoolist/config_stash#readme)
- **Issue Tracker**: [Report Issues](https://github.com/qatoolist/config_stash/issues)
- **Source Code**: [Config-Stash on GitHub](https://github.com/qatoolist/config_stash)