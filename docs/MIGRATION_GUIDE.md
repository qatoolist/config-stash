# Migration Guide

This guide helps you migrate from other configuration management libraries to Config-Stash.

## Table of Contents

- [Migration from python-dotenv](#migration-from-python-dotenv)
- [Migration from Dynaconf](#migration-from-dynaconf)
- [Migration from Hydra/OmegaConf](#migration-from-hydraomegaconf)
- [Migration from Pydantic Settings](#migration-from-pydantic-settings)
- [Migration from python-decouple](#migration-from-python-decouple)
- [CLI Migration Tool](#cli-migration-tool)

---

## Migration from python-dotenv

### Before (python-dotenv)

```python
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_HOST = os.getenv("DATABASE_HOST", "localhost")
DATABASE_PORT = int(os.getenv("DATABASE_PORT", "5432"))
```

### After (Config-Stash)

```python
from config_stash import Config
from config_stash.loaders import YamlLoader, EnvironmentLoader

# Option 1: Use environment variables directly
config = Config(loaders=[EnvironmentLoader("APP")])
database_host = config.database.host
database_port = config.database.port

# Option 2: Use .env file with YamlLoader
config = Config(loaders=[YamlLoader(".env.yaml")])
```

**Key Differences:**
- Config-Stash automatically handles type conversion
- Supports multiple sources (files + environment)
- Provides attribute-style access

**Migration Steps:**
1. Convert `.env` file to YAML format (or use EnvironmentLoader)
2. Replace `os.getenv()` calls with `config.key` access
3. Type casting happens automatically

**CLI Migration:**
```bash
config-stash migrate dotenv .env --output config.yaml
```

---

## Migration from Dynaconf

### Before (Dynaconf)

```python
from dynaconf import Settings

settings = Settings(
    ENV_FOR_DYNACONF="production",
    SETTINGS_FILE_FOR_DYNACONF=["settings.yaml", "production.yaml"]
)

database_host = settings.DATABASE.HOST
```

### After (Config-Stash)

```python
from config_stash import Config
from config_stash.loaders import YamlLoader

config = Config(
    env="production",
    loaders=[
        YamlLoader("settings.yaml"),
        YamlLoader("production.yaml"),
    ]
)

database_host = config.database.host
```

**Key Differences:**
- Config-Stash uses explicit loader list
- Case-insensitive access is optional (default is case-sensitive)
- Better type safety and IDE support

**Migration Steps:**
1. Update environment variable names to use underscores
2. Convert Dynaconf file format (usually YAML) - minimal changes needed
3. Replace `settings.KEY` with `config.key`

**CLI Migration:**
```bash
config-stash migrate dynaconf settings.yaml --output config.yaml
```

---

## Migration from Hydra/OmegaConf

### Before (Hydra)

```python
from hydra import compose, initialize

with initialize(config_path="conf", version_base=None):
    cfg = compose(config_name="config", overrides=["database=postgres"])

database_host = cfg.database.host
```

### After (Config-Stash)

```python
from config_stash import Config
from config_stash.loaders import YamlLoader

config = Config(
    env="production",
    loaders=[YamlLoader("config.yaml")]
)

# Override via CLI or programmatically
config.set("database.host", "postgres")

database_host = config.database.host
```

**Key Differences:**
- Config-Stash doesn't require Hydra's initialization context
- Composition (includes/defaults) is supported via `_include` and `_defaults`
- Simpler API without decorators

**Migration Steps:**
1. Remove Hydra decorators and initialization
2. Convert Hydra config structure (usually compatible)
3. Use Config-Stash's composition directives:
   ```yaml
   # Hydra style
   defaults:
     - database: postgres
   
   # Config-Stash style (compatible)
   _defaults:
     - database: postgres
   ```

**CLI Migration:**
```bash
config-stash migrate hydra conf/config.yaml --output config.yaml
```

---

## Migration from Pydantic Settings

### Before (Pydantic Settings)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_host: str = "localhost"
    database_port: int = 5432
    
    class Config:
        env_prefix = "APP_"

settings = Settings()
```

### After (Config-Stash with Pydantic)

```python
from config_stash import Config
from config_stash.loaders import EnvironmentLoader, YamlLoader
from pydantic import BaseModel

class Settings(BaseModel):
    database_host: str = "localhost"
    database_port: int = 5432

config = Config(
    loaders=[EnvironmentLoader("APP"), YamlLoader("config.yaml")],
    schema=Settings,
    validate_on_load=True,
    strict_validation=True
)

# Access validated config
database_host = config.database_host
database_port = config.database_port
```

**Key Differences:**
- Config-Stash separates schema definition from loading
- Supports multiple sources with schema validation
- Pydantic models can be used for validation

**Migration Steps:**
1. Keep your Pydantic models (they're compatible)
2. Pass model class as `schema` parameter
3. Enable `validate_on_load` for automatic validation

**Benefits:**
- Same validation capabilities
- Additional features: source tracking, hot reload, composition

---

## Migration from python-decouple

### Before (python-decouple)

```python
from decouple import config

DATABASE_HOST = config("DATABASE_HOST", default="localhost")
DATABASE_PORT = config("DATABASE_PORT", default=5432, cast=int)
```

### After (Config-Stash)

```python
from config_stash import Config
from config_stash.loaders import EnvironmentLoader

config = Config(loaders=[EnvironmentLoader("APP")])

# Type casting is automatic
database_host = config.database.host  # or config.get("database.host", "localhost")
database_port = config.database.port
```

**Key Differences:**
- Type casting is automatic (no `cast` parameter needed)
- Supports nested keys via underscores in environment variables
- Multiple configuration sources supported

---

## CLI Migration Tool

Config-Stash provides a CLI tool to automate migration:

```bash
# Migrate from .env file
config-stash migrate dotenv .env --output config.yaml --target-format yaml

# Migrate from Dynaconf
config-stash migrate dynaconf settings.yaml --output config.yaml

# Migrate from Hydra
config-stash migrate hydra conf/config.yaml --output config.yaml
```

The migration tool:
- Preserves configuration values
- Converts format syntax where needed
- Handles nested structures
- Outputs in YAML, JSON, or TOML

---

## Feature Comparison

| Feature | python-dotenv | Dynaconf | Hydra | Pydantic Settings | Config-Stash |
|---------|--------------|----------|-------|-------------------|--------------|
| Multiple sources | ❌ | ✅ | ✅ | ❌ | ✅ |
| Type casting | ❌ | ✅ | ✅ | ✅ | ✅ |
| Schema validation | ❌ | ⚠️ | ✅ | ✅✅ | ✅✅ |
| Hot reload | ❌ | ✅ | ❌ | ❌ | ✅ |
| Source tracking | ❌ | ❌ | ❌ | ❌ | ✅✅ |
| Secret stores | ❌ | ❌ | ❌ | ❌ | ✅ |
| Composition | ❌ | ⚠️ | ✅✅ | ❌ | ✅ |
| IDE support | ❌ | ❌ | ✅ | ✅ | ✅ |

---

## Common Migration Patterns

### Pattern 1: Environment Variables Only

**Before:**
```python
import os
host = os.getenv("DB_HOST", "localhost")
```

**After:**
```python
from config_stash import Config
from config_stash.loaders import EnvironmentLoader
config = Config(loaders=[EnvironmentLoader("DB")])
host = config.host
```

### Pattern 2: File + Environment

**Before:**
```python
import os
config_file = json.load(open("config.json"))
host = os.getenv("DB_HOST") or config_file.get("database", {}).get("host")
```

**After:**
```python
from config_stash import Config
from config_stash.loaders import JsonLoader, EnvironmentLoader
config = Config(loaders=[
    JsonLoader("config.json"),
    EnvironmentLoader("DB")  # Environment overrides file
])
host = config.database.host
```

### Pattern 3: Multiple Environments

**Before:**
```python
env = os.getenv("ENV", "development")
if env == "production":
    config = json.load(open("prod.json"))
else:
    config = json.load(open("dev.json"))
```

**After:**
```python
from config_stash import Config
from config_stash.loaders import YamlLoader
env = os.getenv("ENV", "development")
config = Config(
    env=env,
    loaders=[YamlLoader("config.yaml")]  # Contains dev/prod sections
)
```

---

## Getting Help

If you encounter issues during migration:

1. Use the `lint` command to check for issues:
   ```bash
   config-stash lint production --loader yaml:config.yaml
   ```

2. Use the `debug` command to understand configuration resolution:
   ```bash
   config-stash debug production --key=database.host
   ```

3. Use the `explain` command for detailed resolution information:
   ```bash
   config-stash explain production --key=database.host
   ```

4. Check the [documentation](https://github.com/qatoolist/config-stash#readme) for more examples.

---

## Next Steps

After migration:

1. **Validate your configuration:**
   ```bash
   config-stash validate production --loader yaml:config.yaml
   ```

2. **Enable schema validation:**
   ```python
   config = Config(schema=MySettings, validate_on_load=True)
   ```

3. **Set up hot reloading:**
   ```python
   config = Config(dynamic_reloading=True)
   ```

4. **Integrate secret stores:**
   ```python
   from config_stash.secret_stores import AWSSecretsManager, SecretResolver
   store = AWSSecretsManager(region_name='us-east-1')
   config = Config(secret_resolver=SecretResolver(store))
   ```
