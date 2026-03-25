# pyright: basic
"""Comprehensive example of secret store integration with Config-Stash.

This example demonstrates how to integrate various secret stores (AWS Secrets Manager,
HashiCorp Vault, environment variables, etc.) with your configuration management.
"""

import os
import tempfile
from pathlib import Path

# Example 1: Using DictSecretStore (for development/testing)
def example_dict_secret_store():
    """Simple in-memory secret store for development."""
    print("\n" + "="*60)
    print("Example 1: DictSecretStore (Development/Testing)")
    print("="*60)

    from config_stash import Config
    from config_stash.secret_stores import DictSecretStore, SecretResolver
    from config_stash.loaders import YamlLoader

    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("""
default:
  database:
    host: localhost
    port: 5432
    username: app_user
    password: "${secret:database/password}"

  api:
    endpoint: https://api.example.com
    key: "${secret:api/key}"

  redis:
    url: "redis://:${secret:redis/password}@localhost:6379/0"
""")
        config_file = f.name

    try:
        # Create a secret store with development secrets
        secrets = DictSecretStore({
            "database/password": "dev-password-123",
            "api/key": "dev-api-key-abc123",
            "redis/password": "redis-dev-password",
        })

        # Create config with secret resolver
        config = Config(
            env="default",
            loaders=[YamlLoader(config_file)],
            secret_resolver=SecretResolver(secrets),
            enable_ide_support=False
        )

        print(f"Database password: {config.database.password}")
        print(f"API key: {config.api.key}")
        print(f"Redis URL: {config.redis.url}")
        print("\n✓ Secrets resolved successfully from DictSecretStore")

    finally:
        os.unlink(config_file)


# Example 2: Using Environment Variables as Secret Store
def example_env_secret_store():
    """Use environment variables as a secret source."""
    print("\n" + "="*60)
    print("Example 2: EnvSecretStore (Environment Variables)")
    print("="*60)

    from config_stash import Config
    from config_stash.secret_stores import EnvSecretStore, SecretResolver
    from config_stash.loaders import YamlLoader

    # Set some environment variables
    os.environ["DB_PASSWORD"] = "env-password-456"
    os.environ["API_KEY"] = "env-api-key-xyz789"

    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("""
default:
  database:
    password: "${secret:db/password}"
  api:
    key: "${secret:api/key}"
""")
        config_file = f.name

    try:
        # Create env-based secret store
        # transform_key=True converts "db/password" to "DB_PASSWORD"
        store = EnvSecretStore(transform_key=True)

        config = Config(
            env="default",
            loaders=[YamlLoader(config_file)],
            secret_resolver=SecretResolver(store),
            enable_ide_support=False
        )

        print(f"Database password from env: {config.database.password}")
        print(f"API key from env: {config.api.key}")
        print("\n✓ Secrets resolved from environment variables")

    finally:
        os.unlink(config_file)
        del os.environ["DB_PASSWORD"]
        del os.environ["API_KEY"]


# Example 3: Multi-Store with Fallback
def example_multi_store():
    """Use multiple secret stores with fallback hierarchy."""
    print("\n" + "="*60)
    print("Example 3: MultiSecretStore (Fallback Hierarchy)")
    print("="*60)

    from config_stash import Config
    from config_stash.secret_stores import (
        DictSecretStore,
        EnvSecretStore,
        MultiSecretStore,
        SecretResolver
    )
    from config_stash.loaders import YamlLoader

    # Setup environment
    os.environ["FALLBACK_SECRET"] = "from-environment"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("""
default:
  primary_secret: "${secret:primary/key}"
  override_secret: "${secret:override/key}"
  fallback_secret: "${secret:fallback/secret}"
""")
        config_file = f.name

    try:
        # Create a hierarchy of secret stores
        # 1. Local overrides (highest priority)
        local_overrides = DictSecretStore({
            "override/key": "local-override-value"
        })

        # 2. Application secrets (medium priority)
        app_secrets = DictSecretStore({
            "primary/key": "primary-value",
            "override/key": "this-will-be-overridden"
        })

        # 3. Environment variables (fallback)
        env_store = EnvSecretStore(transform_key=True)

        # Create multi-store with priority order
        multi_store = MultiSecretStore([
            local_overrides,  # Checked first
            app_secrets,      # Checked second
            env_store,        # Fallback
        ])

        config = Config(
            env="default",
            loaders=[YamlLoader(config_file)],
            secret_resolver=SecretResolver(multi_store),
            enable_ide_support=False
        )

        print(f"Primary secret (from app_secrets): {config.primary_secret}")
        print(f"Override secret (from local_overrides): {config.override_secret}")
        print(f"Fallback secret (from env): {config.fallback_secret}")
        print("\n✓ Multi-store fallback hierarchy working correctly")

    finally:
        os.unlink(config_file)
        del os.environ["FALLBACK_SECRET"]


# Example 4: JSON Path Extraction from Secrets
def example_json_path_extraction():
    """Extract nested values from JSON secrets."""
    print("\n" + "="*60)
    print("Example 4: JSON Path Extraction")
    print("="*60)

    from config_stash import Config
    from config_stash.secret_stores import DictSecretStore, SecretResolver
    from config_stash.loaders import YamlLoader

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("""
default:
  database:
    host: "${secret:db-config:connection.host}"
    port: "${secret:db-config:connection.port}"
    user: "${secret:db-config:credentials.username}"
    password: "${secret:db-config:credentials.password}"
""")
        config_file = f.name

    try:
        # Create a secret store with nested JSON structure
        secrets = DictSecretStore({
            "db-config": {
                "connection": {
                    "host": "db.example.com",
                    "port": 5432
                },
                "credentials": {
                    "username": "app_user",
                    "password": "super-secret-pass"
                }
            }
        })

        config = Config(
            env="default",
            loaders=[YamlLoader(config_file)],
            secret_resolver=SecretResolver(secrets),
            enable_ide_support=False
        )

        print(f"DB Host: {config.database.host}")
        print(f"DB Port: {config.database.port}")
        print(f"DB User: {config.database.user}")
        print(f"DB Password: {config.database.password}")
        print("\n✓ JSON path extraction working correctly")

    finally:
        os.unlink(config_file)


# Example 5: Environment-Specific Secret Prefixes
def example_env_prefixed_secrets():
    """Use environment-specific secret prefixes."""
    print("\n" + "="*60)
    print("Example 5: Environment-Specific Secret Prefixes")
    print("="*60)

    from config_stash import Config
    from config_stash.secret_stores import DictSecretStore, SecretResolver
    from config_stash.loaders import YamlLoader

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("""
default:
  api:
    key: "${secret:api/key}"
""")
        config_file = f.name

    try:
        # Create a secret store with environment-prefixed secrets
        all_secrets = DictSecretStore({
            "dev/api/key": "dev-key-123",
            "staging/api/key": "staging-key-456",
            "prod/api/key": "prod-key-789",
        })

        # Use production secrets with prefix
        prod_resolver = SecretResolver(
            all_secrets,
            prefix="prod/"  # Automatically prepends to all lookups
        )

        config = Config(
            env="default",
            loaders=[YamlLoader(config_file)],
            secret_resolver=prod_resolver,
            enable_ide_support=False
        )

        print(f"API Key (production): {config.api.key}")
        print("\n✓ Environment-prefixed secrets resolved correctly")

    finally:
        os.unlink(config_file)


# Example 6: AWS Secrets Manager (requires boto3)
def example_aws_secrets_manager():
    """Example of using AWS Secrets Manager (conceptual)."""
    print("\n" + "="*60)
    print("Example 6: AWS Secrets Manager (Conceptual)")
    print("="*60)

    print("""
To use AWS Secrets Manager in production:

1. Install dependencies:
   pip install boto3

2. Configure AWS credentials (one of):
   - AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables
   - ~/.aws/credentials file
   - IAM role (when running on EC2, ECS, Lambda, etc.)

3. Create the secret store:
   from config_stash.secret_stores import AWSSecretsManager, SecretResolver

   store = AWSSecretsManager(region_name='us-east-1')
   resolver = SecretResolver(store)

   config = Config(
       env='production',
       loaders=[YamlLoader('config.yaml')],
       secret_resolver=resolver
   )

4. In your config file:
   database:
     password: "${secret:prod/db/password}"

   # For JSON secrets with key extraction:
   api:
     key: "${secret:prod/api-config:api_key}"

5. Store secrets in AWS Secrets Manager using AWS Console, CLI, or boto3
""")


# Example 7: HashiCorp Vault (requires hvac)
def example_hashicorp_vault():
    """Example of using HashiCorp Vault (conceptual)."""
    print("\n" + "="*60)
    print("Example 7: HashiCorp Vault (Conceptual)")
    print("="*60)

    print("""
To use HashiCorp Vault in production:

1. Install dependencies:
   pip install hvac

2. Create the Vault client:
   from config_stash.secret_stores import HashiCorpVault, SecretResolver

   # With token auth:
   store = HashiCorpVault(
       url='https://vault.example.com',
       token='your-vault-token',
       mount_point='secret',
       kv_version=2
   )

   # With AppRole auth:
   store = HashiCorpVault(
       url='https://vault.example.com',
       role_id='your-role-id',
       secret_id='your-secret-id'
   )

   resolver = SecretResolver(store)
   config = Config(
       env='production',
       loaders=[YamlLoader('config.yaml')],
       secret_resolver=resolver
   )

3. In your config file:
   database:
     password: "${secret:myapp/database:password}"

   # For KV v2: secret/data/myapp/database
   # For KV v1: secret/myapp/database

4. Store secrets in Vault:
   vault kv put secret/myapp/database \\
     host=db.example.com \\
     password=super-secret
""")


# Example 8: Custom Secret Store Implementation
def example_custom_secret_store():
    """Example of implementing a custom secret store."""
    print("\n" + "="*60)
    print("Example 8: Custom Secret Store Implementation")
    print("="*60)

    from config_stash import Config
    from config_stash.secret_stores.base import SecretStore, SecretNotFoundError
    from config_stash.secret_stores import SecretResolver
    from config_stash.loaders import YamlLoader

    # Custom secret store implementation
    class FileBasedSecretStore(SecretStore):
        """Simple file-based secret store for demonstration."""

        def __init__(self, secrets_dir: str):
            self.secrets_dir = Path(secrets_dir)
            self.secrets_dir.mkdir(exist_ok=True)

        def get_secret(self, key: str, version=None, **kwargs):
            """Read secret from file."""
            file_path = self.secrets_dir / key.replace("/", "_")
            if not file_path.exists():
                raise SecretNotFoundError(f"Secret file not found: {file_path}")
            return file_path.read_text().strip()

        def set_secret(self, key: str, value, **kwargs):
            """Write secret to file."""
            file_path = self.secrets_dir / key.replace("/", "_")
            file_path.write_text(str(value))

        def delete_secret(self, key: str, **kwargs):
            """Delete secret file."""
            file_path = self.secrets_dir / key.replace("/", "_")
            if file_path.exists():
                file_path.unlink()
            else:
                raise SecretNotFoundError(f"Secret file not found: {file_path}")

        def list_secrets(self, prefix=None, **kwargs):
            """List all secret files."""
            secrets = []
            for file_path in self.secrets_dir.glob("*"):
                if file_path.is_file():
                    secret_name = file_path.name.replace("_", "/")
                    if prefix is None or secret_name.startswith(prefix):
                        secrets.append(secret_name)
            return secrets

    # Use the custom store
    with tempfile.TemporaryDirectory() as secrets_dir:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
default:
  api:
    key: "${secret:api/key}"
  database:
    password: "${secret:database/password}"
""")
            config_file = f.name

        try:
            # Create custom store and add secrets
            store = FileBasedSecretStore(secrets_dir)
            store.set_secret("api/key", "custom-api-key-123")
            store.set_secret("database/password", "custom-db-password")

            # Use with Config
            config = Config(
                env="default",
                loaders=[YamlLoader(config_file)],
                secret_resolver=SecretResolver(store),
                enable_ide_support=False
            )

            print(f"API Key: {config.api.key}")
            print(f"Database Password: {config.database.password}")
            print(f"Available secrets: {store.list_secrets()}")
            print("\n✓ Custom secret store working correctly")

        finally:
            os.unlink(config_file)


# Example 9: Secret Caching and Performance
def example_secret_caching():
    """Demonstrate secret caching for performance."""
    print("\n" + "="*60)
    print("Example 9: Secret Caching and Performance")
    print("="*60)

    from config_stash.secret_stores import DictSecretStore, SecretResolver
    import time

    # Create a slow secret store (simulates network calls)
    class SlowSecretStore(DictSecretStore):
        def get_secret(self, key, version=None, **kwargs):
            time.sleep(0.1)  # Simulate 100ms network latency
            return super().get_secret(key, version, **kwargs)

    secrets = SlowSecretStore({
        "api/key": "abc123",
        "db/password": "secret",
        "redis/url": "redis://localhost"
    })

    # Without caching
    resolver_no_cache = SecretResolver(secrets, cache_enabled=False)
    start = time.time()
    for _ in range(10):
        resolver_no_cache.resolve("${secret:api/key}")
    no_cache_time = time.time() - start

    # With caching
    resolver_with_cache = SecretResolver(secrets, cache_enabled=True)
    start = time.time()
    for _ in range(10):
        resolver_with_cache.resolve("${secret:api/key}")
    cache_time = time.time() - start

    print(f"Without cache (10 calls): {no_cache_time:.2f}s")
    print(f"With cache (10 calls): {cache_time:.2f}s")
    print(f"Speedup: {no_cache_time/cache_time:.1f}x faster")

    # Cache statistics
    stats = resolver_with_cache.cache_stats
    print(f"\nCache stats: {stats}")
    print("\n✓ Caching significantly improves performance")


def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("Config-Stash Secret Store Integration Examples")
    print("="*60)

    example_dict_secret_store()
    example_env_secret_store()
    example_multi_store()
    example_json_path_extraction()
    example_env_prefixed_secrets()
    example_custom_secret_store()
    example_secret_caching()

    # Conceptual examples (don't require external services)
    example_aws_secrets_manager()
    example_hashicorp_vault()

    print("\n" + "="*60)
    print("All examples completed successfully!")
    print("="*60)


if __name__ == "__main__":
    main()
