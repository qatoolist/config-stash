# Secret Store Integration

Config-Stash provides a comprehensive and extensible secret store integration system that allows you to securely manage sensitive configuration values using external secret management services.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Supported Secret Stores](#supported-secret-stores)
- [Secret Placeholder Syntax](#secret-placeholder-syntax)
- [Built-in Providers](#built-in-providers)
  - [DictSecretStore](#dictsecretstore)
  - [EnvSecretStore](#envsecretstore)
  - [MultiSecretStore](#multisecretstore)
  - [AWS Secrets Manager](#aws-secrets-manager)
  - [HashiCorp Vault](#hashicorp-vault)
  - [Azure Key Vault](#azure-key-vault)
  - [GCP Secret Manager](#gcp-secret-manager)
- [Custom Secret Stores](#custom-secret-stores)
- [Advanced Features](#advanced-features)
- [Best Practices](#best-practices)

## Overview

The secret store integration provides:

✅ **Pluggable Architecture** - Easy to extend with custom providers
✅ **Multiple Providers** - AWS, Azure, GCP, Vault, and more
✅ **Fallback Support** - Chain multiple stores with priority ordering
✅ **JSON Path Extraction** - Extract nested values from complex secrets
✅ **Caching** - Optional caching for improved performance
✅ **Type Safety** - Full type hints and IDE support

## Quick Start

### Basic Usage

```python
from config_stash import Config
from config_stash.secret_stores import DictSecretStore, SecretResolver
from config_stash.loaders import YamlLoader

# 1. Create a secret store
secrets = DictSecretStore({
    "database/password": "super-secret-password",
    "api/key": "abc123xyz789"
})

# 2. Create a secret resolver
resolver = SecretResolver(secrets)

# 3. Use with Config
config = Config(
    env='production',
    loaders=[YamlLoader('config.yaml')],
    secret_resolver=resolver
)

# Secrets are automatically resolved!
print(config.database.password)  # "super-secret-password"
```

### Configuration File

Your `config.yaml` file contains placeholders:

```yaml
default:
  database:
    host: localhost
    password: "${secret:database/password}"
  api:
    key: "${secret:api/key}"
```

## Secret Placeholder Syntax

Secrets are referenced using the `${secret:key}` placeholder syntax:

```yaml
# Simple secret reference
api_key: "${secret:api/key}"

# JSON path extraction (for nested secrets)
db_password: "${secret:database-config:credentials.password}"

# Within strings
database_url: "postgresql://user:${secret:db/password}@localhost/mydb"

# With version (provider-specific)
old_key: "${secret:api/key::v1}"  # AWS Secrets Manager version
```

### Placeholder Format

```
${secret:<key>:<json_path>:<version>}
```

- **key** (required): The secret identifier
- **json_path** (optional): Dot-notation path for nested values
- **version** (optional): Version identifier (provider-specific)

## Built-in Providers

### DictSecretStore

In-memory dictionary-based store, perfect for development and testing.

```python
from config_stash.secret_stores import DictSecretStore

store = DictSecretStore({
    "api/key": "test-key-123",
    "db/config": {
        "host": "localhost",
        "password": "secret"
    }
})

# Get secret
password = store.get_secret("api/key")

# Set secret
store.set_secret("new/key", "value")

# List secrets
secrets = store.list_secrets(prefix="api/")

# Secret versioning
store.set_secret("api/key", "v1", keep_versions=True)
store.set_secret("api/key", "v2", keep_versions=True)
old_version = store.get_secret("api/key", version="0")
```

**Best For:** Development, testing, unit tests

### EnvSecretStore

Reads secrets from environment variables with automatic key transformation.

```python
from config_stash.secret_stores import EnvSecretStore
import os

# Set environment variables
os.environ['DB_PASSWORD'] = 'secret123'
os.environ['API_KEY'] = 'abc123'

# Create store with key transformation
store = EnvSecretStore(
    prefix="",
    suffix="",
    transform_key=True  # "db/password" → "DB_PASSWORD"
)

# Get secret (automatically transforms key)
password = store.get_secret("db/password")  # Gets DB_PASSWORD

# Without transformation
store = EnvSecretStore(transform_key=False)
password = store.get_secret("DB_PASSWORD")  # Direct lookup
```

**Key Transformation Rules:**
- Replaces `/`, `.`, `-` with `_`
- Converts to uppercase (unless `case_sensitive=True`)
- Adds optional prefix and suffix

**Best For:** CI/CD pipelines, Docker containers, Kubernetes secrets

### MultiSecretStore

Combines multiple secret stores with fallback hierarchy.

```python
from config_stash.secret_stores import (
    MultiSecretStore,
    DictSecretStore,
    EnvSecretStore
)

# Create a fallback hierarchy
primary = DictSecretStore({"override/key": "local-value"})
secondary = DictSecretStore({"db/password": "secret"})
fallback = EnvSecretStore(transform_key=True)

# Priority order: primary → secondary → fallback
multi_store = MultiSecretStore([primary, secondary, fallback])

# Automatically falls through stores
secret = multi_store.get_secret("db/password")  # From secondary

# Find which store has a secret
store = multi_store.get_store_for_secret("override/key")
print(store)  # Returns primary
```

**Best For:** Development overrides, multi-environment setups, gradual migration

### AWS Secrets Manager

Integration with AWS Secrets Manager.

```python
from config_stash.secret_stores import AWSSecretsManager, SecretResolver
from config_stash import Config

# Prerequisites: pip install boto3

# Initialize
store = AWSSecretsManager(
    region_name='us-east-1',
    # Optional: explicit credentials
    # aws_access_key_id='...',
    # aws_secret_access_key='...'
)

# Use with Config
config = Config(
    env='production',
    loaders=[YamlLoader('config.yaml')],
    secret_resolver=SecretResolver(store)
)

# Config file:
# database:
#   password: "${secret:prod/db/password}"
#   config: "${secret:prod/db/config:host}"  # JSON key extraction
```

**Features:**
- Automatic JSON parsing
- Key extraction from JSON secrets using `:key` syntax
- Version support (`version="AWSCURRENT"`, `version="v1-guid"`)
- Automatic credential resolution (env vars, IAM role, etc.)

**Authentication:**
1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. `~/.aws/credentials` file
3. IAM role (when running on EC2, ECS, Lambda, etc.)

**Best For:** AWS-native applications, production workloads

### HashiCorp Vault

Integration with HashiCorp Vault (KV v1 and v2).

```python
from config_stash.secret_stores import HashiCorpVault, SecretResolver

# Prerequisites: pip install hvac

# Token authentication
store = HashiCorpVault(
    url='https://vault.example.com',
    token='your-vault-token',
    mount_point='secret',
    kv_version=2
)

# AppRole authentication
store = HashiCorpVault(
    url='https://vault.example.com',
    role_id='your-role-id',
    secret_id='your-secret-id',
    mount_point='secret',
    kv_version=2
)

# Use with Config
config = Config(
    env='production',
    secret_resolver=SecretResolver(store)
)

# Config file (KV v2):
# database:
#   password: "${secret:myapp/database:password}"
#
# For KV v2: secret/data/myapp/database
# For KV v1: secret/myapp/database
```

**Features:**
- Support for KV v1 and KV v2 engines
- Multiple authentication methods (token, AppRole)
- Version support (KV v2)
- Namespace support (Vault Enterprise)

**Best For:** Multi-cloud deployments, enterprises using Vault

### Azure Key Vault

Integration with Azure Key Vault.

```python
from config_stash.secret_stores import AzureKeyVault, SecretResolver

# Prerequisites: pip install azure-keyvault-secrets azure-identity

# Using default credentials
store = AzureKeyVault(
    vault_url='https://my-vault.vault.azure.net'
)

# Using specific credentials
from azure.identity import ClientSecretCredential

credential = ClientSecretCredential(
    tenant_id='...',
    client_id='...',
    client_secret='...'
)

store = AzureKeyVault(
    vault_url='https://my-vault.vault.azure.net',
    credential=credential
)

# Use with Config
config = Config(
    env='production',
    secret_resolver=SecretResolver(store)
)

# Config file:
# database:
#   password: "${secret:db-password}"  # Note: Use hyphens, not slashes
```

**Important:** Azure Key Vault secret names must match regex: `^[0-9a-zA-Z-]+$`

**Authentication:**
1. Environment variables (`AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`)
2. Managed Identity (when running in Azure)
3. Azure CLI credentials
4. Visual Studio Code credentials

**Best For:** Azure-native applications

### GCP Secret Manager

Integration with Google Cloud Secret Manager.

```python
from config_stash.secret_stores import GCPSecretManager, SecretResolver

# Prerequisites: pip install google-cloud-secret-manager

# Using default credentials
store = GCPSecretManager(project_id='my-gcp-project')

# Using service account
from google.oauth2 import service_account

credentials = service_account.Credentials.from_service_account_file(
    'path/to/service-account-key.json'
)

store = GCPSecretManager(
    project_id='my-gcp-project',
    credentials=credentials
)

# Use with Config
config = Config(
    env='production',
    secret_resolver=SecretResolver(store)
)

# Config file:
# database:
#   password: "${secret:db-password}"
#   old_password: "${secret:db-password::2}"  # Version 2
```

**Authentication:**
1. `GOOGLE_APPLICATION_CREDENTIALS` environment variable
2. `gcloud auth application-default login`
3. Automatic when running on GCP (Compute Engine, Cloud Run, etc.)

**Best For:** GCP-native applications

## Custom Secret Stores

Create your own secret store by extending the `SecretStore` base class:

```python
from config_stash.secret_stores.base import SecretStore, SecretNotFoundError
from typing import Any, List, Optional

class MyCustomSecretStore(SecretStore):
    """Custom secret store implementation."""

    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key
        # Initialize your custom client here

    def get_secret(self, key: str, version: Optional[str] = None, **kwargs) -> Any:
        """Retrieve a secret."""
        try:
            # Your custom implementation
            response = your_api.get_secret(key, version)
            return response.value
        except YourAPINotFoundError:
            raise SecretNotFoundError(f"Secret '{key}' not found")

    def set_secret(self, key: str, value: Any, **kwargs) -> None:
        """Store a secret."""
        your_api.put_secret(key, value)

    def delete_secret(self, key: str, **kwargs) -> None:
        """Delete a secret."""
        your_api.delete_secret(key)

    def list_secrets(self, prefix: Optional[str] = None, **kwargs) -> List[str]:
        """List secrets."""
        secrets = your_api.list_secrets()
        if prefix:
            secrets = [s for s in secrets if s.startswith(prefix)]
        return secrets

# Use your custom store
store = MyCustomSecretStore(api_url='...', api_key='...')
config = Config(secret_resolver=SecretResolver(store))
```

## Advanced Features

### JSON Path Extraction

Extract nested values from complex JSON secrets:

```python
# Secret in store:
{
    "database": {
        "connection": {
            "host": "db.example.com",
            "port": 5432
        },
        "credentials": {
            "username": "admin",
            "password": "secret"
        }
    }
}

# Config file:
database:
  host: "${secret:db-config:database.connection.host}"
  password: "${secret:db-config:database.credentials.password}"
```

### Secret Caching

Enable caching to improve performance:

```python
# Enable caching (default: True)
resolver = SecretResolver(store, cache_enabled=True)

# Prefetch secrets
resolver.prefetch_secrets([
    "database/password",
    "api/key",
    "redis/url"
])

# Clear cache (e.g., after secret rotation)
resolver.clear_cache()

# Check cache stats
stats = resolver.cache_stats
print(f"Cached secrets: {stats['size']}")
```

### Environment-Specific Prefixes

Use prefixes to organize secrets by environment:

```python
# Store secrets with environment prefixes
secrets = DictSecretStore({
    "dev/api/key": "dev-key",
    "staging/api/key": "staging-key",
    "prod/api/key": "prod-key"
})

# Use environment-specific prefix
prod_resolver = SecretResolver(secrets, prefix="prod/")

# Config file uses unprefixed keys
# api:
#   key: "${secret:api/key}"

# Automatically resolves to "prod/api/key"
```

### Fail-Safe Mode

Control behavior when secrets are missing:

```python
# Fail on missing secrets (default: True)
resolver = SecretResolver(store, fail_on_missing=True)

# Leave placeholders unchanged if secret not found
resolver = SecretResolver(store, fail_on_missing=False)

# Config:
# api_key: "${secret:nonexistent}"

# With fail_on_missing=False: api_key remains "${secret:nonexistent}"
# With fail_on_missing=True: raises SecretNotFoundError
```

## Best Practices

### 1. Use Environment-Specific Configuration

```python
# Development
if ENV == 'development':
    store = DictSecretStore({...})  # Local secrets

# Production
else:
    store = AWSSecretsManager(region_name='us-east-1')

config = Config(
    env=ENV,
    secret_resolver=SecretResolver(store)
)
```

### 2. Implement Fallback Hierarchy

```python
multi_store = MultiSecretStore([
    DictSecretStore({...}),      # Local overrides (highest priority)
    AWSSecretsManager(...),      # Production secrets
    EnvSecretStore(),            # Environment variables (fallback)
])
```

### 3. Enable Caching for Performance

```python
# Cache secrets to reduce API calls
resolver = SecretResolver(store, cache_enabled=True)

# Prefetch commonly used secrets at startup
resolver.prefetch_secrets([
    "database/password",
    "api/key",
    "redis/url"
])
```

### 4. Use Descriptive Secret Keys

```yaml
# Good
database:
  password: "${secret:prod/postgres/password}"

# Better
database:
  password: "${secret:prod/myapp/postgres/master/password}"
```

### 5. Rotate Secrets Regularly

```python
# After rotating secrets in your secret store
config.reload()  # Reload configuration
resolver.clear_cache()  # Clear cached secrets
```

### 6. Never Commit Secrets

```bash
# .gitignore
.env
secrets.yaml
*.key
*.pem
```

### 7. Use IAM/RBAC for Access Control

Configure minimal permissions for your application:

**AWS IAM Policy Example:**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["secretsmanager:GetSecretValue"],
    "Resource": "arn:aws:secretsmanager:us-east-1:123456789:secret:myapp/*"
  }]
}
```

### 8. Monitor Secret Access

Enable audit logging in your secret store:
- AWS: CloudTrail
- Azure: Activity Log
- GCP: Cloud Audit Logs
- Vault: Audit device

### 9. Test with Mock Stores

```python
# In tests
def test_my_app():
    test_secrets = DictSecretStore({
        "api/key": "test-key",
        "db/password": "test-password"
    })

    config = Config(
        env='test',
        secret_resolver=SecretResolver(test_secrets)
    )

    # Test your application
```

### 10. Handle Secret Store Failures Gracefully

```python
from config_stash.secret_stores.base import SecretStoreError

try:
    config = Config(secret_resolver=resolver)
except SecretStoreError as e:
    logger.error(f"Failed to load secrets: {e}")
    # Fallback or fail gracefully
```

## Examples

See [`examples/secret_store_example.py`](../examples/secret_store_example.py) for comprehensive examples covering all features.

## Troubleshooting

### Placeholders Not Being Resolved

1. Verify secret resolver is passed to Config:
   ```python
   config = Config(secret_resolver=SecretResolver(store))
   ```

2. Check placeholder syntax:
   ```yaml
   password: "${secret:key}"  # Correct
   password: "$secret:key"    # Wrong - missing braces
   ```

3. Verify secret exists in store:
   ```python
   print(store.list_secrets())
   ```

### Authentication Errors

- **AWS**: Check IAM permissions and credential configuration
- **Azure**: Verify Azure AD permissions and managed identity
- **GCP**: Check service account permissions
- **Vault**: Verify token/AppRole permissions

### Performance Issues

- Enable caching: `SecretResolver(store, cache_enabled=True)`
- Prefetch secrets: `resolver.prefetch_secrets([...])`
- Use connection pooling in your secret store
- Consider caching at infrastructure level (e.g., AWS Secrets Manager caching)

## License

This feature is part of Config-Stash and follows the same license.
