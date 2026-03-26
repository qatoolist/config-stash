# Migration Guide

This guide helps you migrate from other configuration management libraries to Config-Stash.

Throughout this guide, we use the `cs` short alias for imports. Both `cs` and `config_stash` work identically:

```python
from cs import Config              # short form
from config_stash import Config    # also works
```

---

## Table of Contents

- [Why Migrate?](#why-migrate)
- [Migration from python-dotenv](#migration-from-python-dotenv)
- [Migration from python-decouple](#migration-from-python-decouple)
- [Migration from OmegaConf](#migration-from-omegaconf)
- [Migration from Dynaconf](#migration-from-dynaconf)
- [Migration from Hydra](#migration-from-hydra)
- [Migration from Pydantic Settings](#migration-from-pydantic-settings)
- [Automated Migration (CLI)](#automated-migration-cli)
- [Feature Comparison](#feature-comparison)
- [Common Migration Patterns](#common-migration-patterns)
- [Post-Migration Checklist](#post-migration-checklist)
- [Getting Help](#getting-help)

---

## Why Migrate?

### What You Gain

| Capability | What it means |
|---|---|
| **Unified multi-source loading** | YAML, JSON, TOML, INI, env vars, S3, SSM, Azure Blob, GCP Storage, Git — one API |
| **`Config[T]` typed access** | Full IDE autocomplete and mypy/pyright checking via `.typed` property |
| **Secret store integration** | AWS Secrets Manager, Azure Key Vault, GCP Secret Manager, HashiCorp Vault (10 auth methods) |
| **Source tracking** | `config.get_source("database.host")` tells you which file set each value |
| **Hot reload** | File watcher detects changes and reloads automatically |
| **Composition** | `_include` and `_defaults` directives for composing configs from fragments |
| **Config diffing** | Compare two config states programmatically |

### What You Keep

- **Pydantic models work unchanged.** Pass your existing `BaseModel` as `schema=` and it just works.
- **YAML/JSON/TOML files are compatible.** No format conversion needed for standard files.
- **Environment variables still work.** `EnvironmentLoader` reads them with prefix-based nesting.

### What's Different (Tradeoffs)

| Area | Detail |
|---|---|
| **No variable interpolation** | Config-Stash does not support `${db.host}`-style interpolation within config values. Use `${ENV_VAR}` expansion for environment variables instead. |
| **No multirun/sweep** | Hydra's experiment sweep feature has no equivalent. Use an external orchestrator. |
| **No `instantiate()`** | Hydra's `hydra.utils.instantiate()` for object creation is not provided. |
| **Learning curve** | If your team is deeply invested in another tool, migration has a cost. Evaluate whether the added capabilities justify it. |

---

## Migration from python-dotenv

### Before (python-dotenv)

```python
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_HOST = os.getenv("DATABASE_HOST", "localhost")
DATABASE_PORT = int(os.getenv("DATABASE_PORT", "5432"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
```

### After (Config-Stash) — Untyped

```python
from cs import Config
from cs.loaders import EnvironmentLoader

config = Config(loaders=[EnvironmentLoader("APP")])

# Attribute access with automatic type casting
database_host = config.database.host
database_port = config.database.port  # auto-cast to int
```

### After (Config-Stash) — Typed with `Config[T]`

```python
from pydantic import BaseModel
from cs import Config
from cs.loaders import EnvironmentLoader, YamlLoader

class AppConfig(BaseModel):
    database_host: str = "localhost"
    database_port: int = 5432
    debug: bool = False

config = Config[AppConfig](
    loaders=[
        YamlLoader("config.yaml"),       # base config file
        EnvironmentLoader("APP"),         # env vars override file values
    ],
    schema=AppConfig,
    validate_on_load=True,
)

# Full IDE autocomplete — your editor knows the types
host = config.typed.database_host   # IDE knows: str
port = config.typed.database_port   # IDE knows: int
debug = config.typed.debug          # IDE knows: bool
```

### Step-by-Step Checklist

1. Install Config-Stash: `pip install config-stash`
2. Convert your `.env` file to YAML (or keep it and use `EnvironmentLoader`)
3. Replace `os.getenv()` calls with `config.key` attribute access
4. Remove `load_dotenv()` calls
5. (Optional) Define a Pydantic model for typed access
6. Remove `python-dotenv` from your dependencies

### CLI Migration

```bash
config-stash migrate dotenv .env --output config.yaml
```

This converts `KEY=value` pairs to a flat YAML file. Nested keys using `__` separators (e.g., `DATABASE__HOST`) are converted to nested YAML structures.

---

## Migration from python-decouple

### Before (python-decouple)

```python
from decouple import config, Csv

DATABASE_HOST = config("DATABASE_HOST", default="localhost")
DATABASE_PORT = config("DATABASE_PORT", default=5432, cast=int)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=Csv())
```

### After (Config-Stash) — Untyped

```python
from cs import Config
from cs.loaders import EnvironmentLoader

config = Config(loaders=[EnvironmentLoader("APP")])

# Type casting is automatic — no cast= parameter needed
database_host = config.database.host
database_port = config.database.port
```

### After (Config-Stash) — Typed with `Config[T]`

```python
from typing import List
from pydantic import BaseModel
from cs import Config
from cs.loaders import EnvironmentLoader

class AppConfig(BaseModel):
    database_host: str = "localhost"
    database_port: int = 5432
    allowed_hosts: List[str] = ["localhost"]

config = Config[AppConfig](
    loaders=[EnvironmentLoader("APP")],
    schema=AppConfig,
    validate_on_load=True,
)

hosts = config.typed.allowed_hosts  # IDE knows: List[str]
```

### Step-by-Step Checklist

1. Install Config-Stash: `pip install config-stash`
2. Replace `from decouple import config` with Config-Stash setup
3. Remove `cast=` arguments — type casting is automatic, or use a Pydantic schema
4. Replace `config("KEY")` calls with `config.key` attribute access
5. Remove `python-decouple` from your dependencies

---

## Migration from OmegaConf

OmegaConf is widely used in ML/data science pipelines, often alongside Hydra. This section covers standalone OmegaConf usage.

### Loading YAML files

**Before (OmegaConf):**

```python
from omegaconf import OmegaConf

cfg = OmegaConf.load("config.yaml")
host = cfg.database.host
```

**After (Config-Stash):**

```python
from cs import Config
from cs.loaders import YamlLoader

config = Config(loaders=[YamlLoader("config.yaml")])
host = config.database.host
```

### Merging configs

**Before (OmegaConf):**

```python
from omegaconf import OmegaConf

base = OmegaConf.load("base.yaml")
overrides = OmegaConf.load("overrides.yaml")
cfg = OmegaConf.merge(base, overrides)
```

**After (Config-Stash):**

```python
from cs import Config
from cs.loaders import YamlLoader

# Later loaders override earlier loaders (deep merge by default)
config = Config(loaders=[
    YamlLoader("base.yaml"),
    YamlLoader("overrides.yaml"),
])
```

Config-Stash deep-merges by default. For more control, use `merge_strategy` and `merge_strategy_map`:

```python
from cs import Config
from cs.loaders import YamlLoader
from cs.merge_strategies import MergeStrategy

config = Config(
    loaders=[YamlLoader("base.yaml"), YamlLoader("overrides.yaml")],
    merge_strategy=MergeStrategy.DEEP_MERGE,
    merge_strategy_map={
        "database.replicas": MergeStrategy.REPLACE,  # replace list instead of merging
    },
)
```

### Converting to plain dict

**Before (OmegaConf):**

```python
plain = OmegaConf.to_container(cfg, resolve=True)
```

**After (Config-Stash):**

```python
plain = config.to_dict()
```

### Variable interpolation

OmegaConf supports `${db.host}` references inside config values. Config-Stash does **not** have cross-key interpolation. It does support environment variable expansion:

```yaml
# OmegaConf style (NOT supported):
url: "http://${db.host}:${db.port}/mydb"

# Config-Stash style (environment variable expansion):
url: "http://${DB_HOST}:${DB_PORT}/mydb"
```

If you rely heavily on cross-key interpolation, you have two options:

1. **Pre-resolve** interpolation before loading (e.g., with a build step)
2. **Use environment variables** to share values across config keys

### Structured configs → `Config[T]`

**Before (OmegaConf structured configs):**

```python
from dataclasses import dataclass
from omegaconf import OmegaConf, MISSING

@dataclass
class DBConfig:
    host: str = MISSING
    port: int = 5432

@dataclass
class AppConfig:
    db: DBConfig = DBConfig()

cfg = OmegaConf.structured(AppConfig)
cfg.merge_with(OmegaConf.load("config.yaml"))
```

**After (Config-Stash with Pydantic):**

```python
from pydantic import BaseModel
from cs import Config
from cs.loaders import YamlLoader

class DBConfig(BaseModel):
    host: str
    port: int = 5432

class AppConfig(BaseModel):
    db: DBConfig

config = Config[AppConfig](
    loaders=[YamlLoader("config.yaml")],
    schema=AppConfig,
    validate_on_load=True,
)

config.typed.db.host   # IDE knows: str
config.typed.db.port   # IDE knows: int
```

### Step-by-Step Checklist

1. Install Config-Stash: `pip install config-stash`
2. Replace `OmegaConf.load()` with `YamlLoader`
3. Replace `OmegaConf.merge()` with multiple loaders (later overrides earlier)
4. Replace `OmegaConf.to_container()` with `config.to_dict()`
5. Replace `@dataclass` structured configs with Pydantic `BaseModel` + `Config[T]`
6. Refactor any `${key.ref}` interpolation to use env vars or pre-resolve
7. Remove `omegaconf` from your dependencies

---

## Migration from Dynaconf

### Basic usage

**Before (Dynaconf):**

```python
from dynaconf import Settings

settings = Settings(
    ENV_FOR_DYNACONF="production",
    SETTINGS_FILE_FOR_DYNACONF=["settings.yaml", "production.yaml"],
)

database_host = settings.DATABASE.HOST
```

**After (Config-Stash) — Untyped:**

```python
from cs import Config
from cs.loaders import YamlLoader

config = Config(
    env="production",
    loaders=[
        YamlLoader("settings.yaml"),
        YamlLoader("production.yaml"),
    ],
)

database_host = config.database.host
```

### Environment switching

**Before (Dynaconf):**

```python
from dynaconf import Settings

settings = Settings()

# Switch environment at runtime
settings.from_env("production")

# Or use decorator
@settings.use_env("production")
def get_db_url():
    return settings.DATABASE_URL
```

**After (Config-Stash):**

```python
from cs import Config
from cs.loaders import YamlLoader

# Set environment at construction time
config = Config(env="production", loaders=[YamlLoader("settings.yaml")])

# Or load env vars with a prefix
config = Config(env_prefix="MYAPP", loaders=[YamlLoader("settings.yaml")])
```

Config-Stash sets the environment at construction time. If you need multiple environments simultaneously, create multiple `Config` instances.

### Dynaconf Vault integration → Config-Stash secret stores

**Before (Dynaconf):**

```python
# settings.yaml
# VAULT_ENABLED_FOR_DYNACONF: true
# VAULT_URL_FOR_DYNACONF: https://vault.example.com

from dynaconf import Settings
settings = Settings()
db_password = settings.DATABASE_PASSWORD  # reads from Vault
```

**After (Config-Stash):**

```python
from cs import Config
from cs.loaders import YamlLoader
from cs.secret_stores import HashiCorpVault, SecretResolver

vault = HashiCorpVault(
    url="https://vault.example.com",
    auth_method="approle",             # or token, kubernetes, ldap, oidc, aws, azure, gcp, jwt
    role_id="my-role-id",
    secret_id="my-secret-id",
)

config = Config(
    loaders=[YamlLoader("config.yaml")],
    secret_resolver=SecretResolver(vault),
)
```

Config-Stash supports **10 Vault auth methods** (token, AppRole, Kubernetes, LDAP, OIDC, AWS IAM, Azure, GCP, JWT, userpass) compared to Dynaconf's token-based auth. It also supports AWS Secrets Manager, Azure Key Vault, GCP Secret Manager, and multi-store fallback via `MultiSecretStore`.

In your config files, reference secrets with the `${secret:path}` syntax:

```yaml
database:
  password: "${secret:db/password}"
  api_key: "${secret:services/api-key}"
```

### Dynaconf validators → Pydantic with `Config[T]`

**Before (Dynaconf):**

```python
from dynaconf import Settings, Validator

settings = Settings(
    validators=[
        Validator("DATABASE.HOST", must_exist=True),
        Validator("DATABASE.PORT", gte=1024, lte=65535),
    ]
)
```

**After (Config-Stash):**

```python
from pydantic import BaseModel, Field
from cs import Config
from cs.loaders import YamlLoader

class DatabaseConfig(BaseModel):
    host: str                                          # required (must exist)
    port: int = Field(ge=1024, le=65535, default=5432) # range validation

class AppConfig(BaseModel):
    database: DatabaseConfig

config = Config[AppConfig](
    loaders=[YamlLoader("settings.yaml")],
    schema=AppConfig,
    validate_on_load=True,
    strict_validation=True,  # raise on validation failure
)

config.typed.database.host  # IDE knows: str
config.typed.database.port  # IDE knows: int
```

Pydantic gives you richer validation (regex patterns, custom validators, nested models, union types) than Dynaconf's built-in validators.

### Step-by-Step Checklist

1. Install Config-Stash: `pip install config-stash`
2. Replace `from dynaconf import Settings` with `from cs import Config`
3. Convert `Settings(ENV_FOR_DYNACONF="x")` to `Config(env="x")`
4. Convert `SETTINGS_FILE_FOR_DYNACONF=["a.yaml"]` to `loaders=[YamlLoader("a.yaml")]`
5. Replace `settings.KEY` with `config.key` (Config-Stash is case-sensitive by default)
6. If using Dynaconf Vault: set up `HashiCorpVault` + `SecretResolver`
7. If using Dynaconf validators: convert to a Pydantic `BaseModel`
8. Remove Dynaconf env vars (`*_FOR_DYNACONF`) from your environment
9. Remove `dynaconf` from your dependencies

### CLI Migration

```bash
config-stash migrate dynaconf settings.yaml --output config.yaml
```

This parses the YAML (or JSON) file and outputs a clean Config-Stash-compatible file. You will still need to manually update your Python code.

---

## Migration from Hydra

### Removing the `@hydra.main()` decorator

**Before (Hydra):**

```python
import hydra
from omegaconf import DictConfig

@hydra.main(config_path="conf", config_name="config", version_base=None)
def main(cfg: DictConfig) -> None:
    print(cfg.database.host)

if __name__ == "__main__":
    main()
```

**After (Config-Stash):**

```python
from cs import Config
from cs.loaders import YamlLoader

def main() -> None:
    config = Config(loaders=[YamlLoader("conf/config.yaml")])
    print(config.database.host)

if __name__ == "__main__":
    main()
```

No decorator, no special entry point, no working directory changes. Config is just a regular object you create when you need it.

### Config groups → `_include` composition

**Before (Hydra) — `conf/config.yaml`:**

```yaml
defaults:
  - database: postgres
  - server: nginx

app:
  name: myapp
```

With separate files `conf/database/postgres.yaml` and `conf/server/nginx.yaml`.

**After (Config-Stash) — `config.yaml`:**

```yaml
_include:
  - conf/database/postgres.yaml
  - conf/server/nginx.yaml

app:
  name: myapp
```

Or using `_defaults`:

```yaml
_defaults:
  - database: postgres
  - server: nginx

app:
  name: myapp
```

Config-Stash processes `_include` and `_defaults` directives to compose configs from multiple fragments, with cycle detection for recursive includes.

### `defaults:` list → `_defaults:` directive

The mapping is straightforward — rename the key:

| Hydra | Config-Stash |
|---|---|
| `defaults:` | `_defaults:` |
| `- database: postgres` | `- database: postgres` |
| `- override database: mysql` | Not supported — use a separate override loader |

### `hydra.utils.instantiate()` — No equivalent

Hydra can instantiate Python objects from config:

```yaml
model:
  _target_: torch.nn.Linear
  in_features: 128
  out_features: 10
```

Config-Stash does **not** provide object instantiation from config. This is a deliberate design choice — config loading and object construction are separate concerns. If you need this pattern, instantiate objects in your application code:

```python
from cs import Config
from cs.loaders import YamlLoader
import torch.nn

config = Config(loaders=[YamlLoader("config.yaml")])

# Instantiate manually
model = torch.nn.Linear(
    in_features=config.model.in_features,
    out_features=config.model.out_features,
)
```

### Multirun/sweep — No equivalent

Hydra's `--multirun` feature for hyperparameter sweeps:

```bash
python train.py --multirun learning_rate=0.001,0.01,0.1
```

Config-Stash does not provide experiment sweep functionality. Use an external tool (Optuna, Weights & Biases, Ray Tune) for hyperparameter sweeps and pass config values via environment variables or separate config files.

### Structured configs → `Config[T]`

**Before (Hydra + OmegaConf):**

```python
from dataclasses import dataclass
from hydra.core.config_store import ConfigStore

@dataclass
class DBConfig:
    host: str = "localhost"
    port: int = 5432

cs = ConfigStore.instance()
cs.store(name="db", node=DBConfig)
```

**After (Config-Stash):**

```python
from pydantic import BaseModel
from cs import Config
from cs.loaders import YamlLoader

class DBConfig(BaseModel):
    host: str = "localhost"
    port: int = 5432

class AppConfig(BaseModel):
    db: DBConfig = DBConfig()

config = Config[AppConfig](
    loaders=[YamlLoader("config.yaml")],
    schema=AppConfig,
    validate_on_load=True,
)

config.typed.db.host   # IDE knows: str
config.typed.db.port   # IDE knows: int
```

### Step-by-Step Checklist

1. Install Config-Stash: `pip install config-stash`
2. Remove `@hydra.main()` decorator from your entry point
3. Replace `initialize()` / `compose()` with `Config(loaders=[...])`
4. Rename `defaults:` to `_defaults:` in your YAML files (or use `_include:`)
5. Replace `cfg.key` with `config.key` (same attribute access pattern)
6. Convert `@dataclass` structured configs to Pydantic `BaseModel` (optional)
7. Replace `hydra.utils.instantiate()` with manual object construction
8. Replace multirun/sweep with an external tool
9. Remove `hydra-core` and `omegaconf` from your dependencies

### CLI Migration

```bash
config-stash migrate hydra conf/config.yaml --output config.yaml
```

This strips Hydra-specific keys (`defaults`, `hydra`) from the YAML and outputs a clean file. Config group references are **not** auto-resolved — you will need to convert them to `_include` directives manually.

---

## Migration from Pydantic Settings

### The limitation of pydantic-settings

`pydantic-settings` validates config and gives you typed access, but it can only load from:
- Environment variables
- `.env` files
- (with extras) Azure Key Vault, AWS Secrets Manager

It cannot load from YAML, JSON, TOML, INI, S3, SSM, Git repos, or HTTP endpoints.

### Before (pydantic-settings)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_host: str = "localhost"
    database_port: int = 5432
    redis_url: str = "redis://localhost:6379"

    class Config:
        env_prefix = "APP_"
        env_file = ".env"

settings = Settings()
host = settings.database_host   # IDE knows: str
```

### After (Config-Stash) — Same typing, more sources

```python
from pydantic import BaseModel
from cs import Config
from cs.loaders import YamlLoader, EnvironmentLoader, SSMLoader

class Settings(BaseModel):
    database_host: str = "localhost"
    database_port: int = 5432
    redis_url: str = "redis://localhost:6379"

config = Config[Settings](
    loaders=[
        YamlLoader("config.yaml"),          # base config from file
        SSMLoader("/myapp/production"),      # AWS SSM Parameter Store
        EnvironmentLoader("APP"),            # env vars override everything
    ],
    schema=Settings,
    validate_on_load=True,
    strict_validation=True,
)

# Same typed access as pydantic-settings
host = config.typed.database_host   # IDE knows: str
port = config.typed.database_port   # IDE knows: int
url = config.typed.redis_url        # IDE knows: str
```

The `Config[T].typed` property is the key feature: you get the same Pydantic-validated, IDE-aware typed access that pydantic-settings provides, but your config can come from any combination of sources.

### What changes, what stays the same

| | pydantic-settings | Config-Stash with `Config[T]` |
|---|---|---|
| **Pydantic model** | `BaseSettings` (subclass) | `BaseModel` (standard) |
| **Typed access** | `settings.field` | `config.typed.field` |
| **Env var loading** | Built-in | `EnvironmentLoader("PREFIX")` |
| **File loading** | `.env` only | YAML, JSON, TOML, INI |
| **Cloud sources** | Limited extras | S3, SSM, Azure Blob, GCP Storage, HTTP, Git |
| **Secret stores** | Limited extras | AWS SM, Azure KV, GCP SM, HashiCorp Vault (10 auth methods) |
| **Hot reload** | No | `dynamic_reloading=True` |
| **Source tracking** | No | `config.get_source("key")` |

### Step-by-Step Checklist

1. Install Config-Stash: `pip install config-stash`
2. Change `BaseSettings` to `BaseModel` (remove `class Config` inner class)
3. Create a `Config[YourModel]` instance with your loaders
4. Replace `settings.field` with `config.typed.field`
5. Replace `env_prefix` in `class Config` with `EnvironmentLoader("PREFIX")` or `env_prefix="PREFIX"`
6. (Optional) Add file loaders, SSM, secret stores
7. Remove `pydantic-settings` from your dependencies (keep `pydantic`)

---

## Automated Migration (CLI)

Config-Stash provides a CLI tool that converts config **files** from other formats:

```bash
# Convert .env to YAML
config-stash migrate dotenv .env --output config.yaml

# Convert Dynaconf settings file
config-stash migrate dynaconf settings.yaml --output config.yaml

# Convert Hydra config (strips Hydra-specific keys)
config-stash migrate hydra conf/config.yaml --output config.yaml
```

### What the CLI does

- **dotenv/env:** Parses `KEY=value` pairs and converts to YAML. Nested keys using `__` separators (e.g., `DATABASE__HOST=localhost`) become nested YAML structures.
- **dynaconf:** Parses the YAML/JSON settings file and outputs it in the target format. No structural changes needed for most files.
- **hydra:** Parses the YAML config, strips `defaults:` and `hydra:` keys, and outputs the remaining config.

### What the CLI does NOT do

- It does **not** rewrite your Python code. You still need to update `import` statements and config access patterns manually.
- It does **not** resolve Hydra config group references. `_defaults` entries need manual conversion to `_include` paths.
- It does **not** migrate secrets or environment-specific logic.

### Output format options

```bash
# Output as JSON instead of YAML
config-stash migrate dotenv .env --output config.json --target-format json

# Output as TOML
config-stash migrate dotenv .env --output config.toml --target-format toml

# Print to stdout (no --output flag)
config-stash migrate dotenv .env
```

---

## Feature Comparison

| Feature | python-dotenv | python-decouple | OmegaConf | Dynaconf | Hydra | pydantic-settings | **Config-Stash** |
|---|---|---|---|---|---|---|---|
| **Multiple file formats** | - | - | YAML | YAML, JSON, TOML, INI | YAML | .env | YAML, JSON, TOML, INI |
| **Environment variables** | Load to `os.environ` | Read from env | - | Yes | Yes (via plugin) | Yes | Yes |
| **Type casting** | - | Manual `cast=` | Yes | Yes | Yes | Pydantic | Auto + Pydantic |
| **Schema validation** | - | - | Structured configs | Basic validators | Structured configs | Pydantic | Pydantic + JSON Schema |
| **Typed IDE access** | - | - | Limited | - | Via structured | Yes | Yes (`Config[T].typed`) |
| **Hot reload** | - | - | - | Yes | - | - | Yes |
| **Source tracking** | - | - | - | - | - | - | Yes |
| **Secret stores** | - | - | - | ⚠️ Vault (token auth) | - | ⚠️ Limited extras | AWS SM, Azure KV, GCP SM, Vault (10 auth methods) |
| **Cloud config sources** | - | - | - | ⚠️ Redis, Vault | - | - | S3, SSM, Azure Blob, GCP Storage, HTTP, Git |
| **Config composition** | - | - | Merge | ⚠️ Basic | Yes | - | `_include`, `_defaults` |
| **Config diffing** | - | - | - | - | - | - | Yes |
| **Variable interpolation** | - | - | `${key.ref}` | `@format {this.key}` | `${key.ref}` | - | `${ENV_VAR}` only |
| **Multirun/sweep** | - | - | - | - | Yes | - | - |
| **Object instantiation** | - | - | - | - | `instantiate()` | - | - |

Legend: **Yes** = full support, **⚠️** = partial/limited support, **-** = not supported

---

## Common Migration Patterns

### Pattern 1: Environment variables only

**Before:**

```python
import os
host = os.getenv("DB_HOST", "localhost")
port = int(os.getenv("DB_PORT", "5432"))
```

**After:**

```python
from cs import Config
from cs.loaders import EnvironmentLoader

config = Config(loaders=[EnvironmentLoader("DB")])
host = config.host
port = config.port
```

### Pattern 2: File + environment overrides

**Before:**

```python
import json, os

with open("config.json") as f:
    file_config = json.load(f)

host = os.getenv("DB_HOST") or file_config.get("database", {}).get("host")
```

**After:**

```python
from cs import Config
from cs.loaders import JsonLoader, EnvironmentLoader

config = Config(loaders=[
    JsonLoader("config.json"),
    EnvironmentLoader("DB"),    # env vars override file values
])
host = config.database.host
```

### Pattern 3: Multiple environments

**Before:**

```python
import json, os

env = os.getenv("ENV", "development")
if env == "production":
    config = json.load(open("prod.json"))
else:
    config = json.load(open("dev.json"))
```

**After:**

```python
from cs import Config
from cs.loaders import YamlLoader

config = Config(
    env="production",
    loaders=[YamlLoader("config.yaml")],  # contains environment sections
)
```

Your `config.yaml` uses environment sections:

```yaml
default:
  database:
    host: localhost
    port: 5432

production:
  database:
    host: db.prod.example.com
    port: 5432
```

### Pattern 4: Secrets from Vault + config from files

```python
from cs import Config
from cs.loaders import YamlLoader, EnvironmentLoader
from cs.secret_stores import HashiCorpVault, SecretResolver

vault = HashiCorpVault(
    url="https://vault.example.com",
    auth_method="kubernetes",
    role="my-app",
)

config = Config(
    env="production",
    loaders=[
        YamlLoader("config.yaml"),
        EnvironmentLoader("APP"),
    ],
    secret_resolver=SecretResolver(vault),
)

# In config.yaml:
#   database:
#     password: "${secret:db/password}"
db_password = config.database.password  # resolved from Vault at load time
```

### Pattern 5: Builder pattern for complex setups

```python
from cs import Config
from cs.loaders import YamlLoader, EnvironmentLoader
from cs.secret_stores import AWSSecretsManager, SecretResolver

config = Config.builder() \
    .with_env("production") \
    .add_loader(YamlLoader("base.yaml")) \
    .add_loader(YamlLoader("production.yaml")) \
    .add_loader(EnvironmentLoader("APP")) \
    .with_secrets(SecretResolver(AWSSecretsManager(region_name="us-east-1"))) \
    .enable_dynamic_reloading() \
    .enable_debug() \
    .build()
```

---

## Post-Migration Checklist

After migration, take advantage of Config-Stash features:

### 1. Validate your configuration

```bash
config-stash validate production --loader yaml:config.yaml
```

### 2. Enable schema validation

```python
config = Config(schema=MySettings, validate_on_load=True, strict_validation=True)
```

### 3. Set up hot reloading (if needed)

```python
config = Config(dynamic_reloading=True, loaders=[YamlLoader("config.yaml")])

# Register a callback for config changes
config.on_change(lambda old, new: print(f"Config changed: {old} -> {new}"))
```

### 4. Integrate secret stores

```python
from cs.secret_stores import AWSSecretsManager, SecretResolver

store = AWSSecretsManager(region_name="us-east-1")
config = Config(secret_resolver=SecretResolver(store))
```

### 5. Use the debug tools

```bash
# Lint config for issues
config-stash lint production --loader yaml:config.yaml

# Debug key resolution
config-stash debug production --key=database.host

# Explain where a value came from
config-stash explain production --key=database.host
```

### 6. Freeze config in production

```python
config = Config(loaders=[YamlLoader("config.yaml")])
config.freeze()  # prevents set() and reload() — fully thread-safe
```

---

## Getting Help

If you encounter issues during migration:

1. **Check the CLI debug tools** (see above)
2. **Check the [documentation](https://github.com/qatoolist/config-stash#readme)** for API details
3. **File an issue** on GitHub with your before/after code and the error you see
