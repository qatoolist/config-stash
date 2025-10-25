"""Secret store integration for Config-Stash.

This module provides a pluggable architecture for integrating various secret storage
systems (AWS Secrets Manager, Azure Key Vault, GCP Secret Manager, HashiCorp Vault, etc.)
into your configuration management.

Example:
    >>> from config_stash import Config
    >>> from config_stash.secret_stores import AWSSecretsManager, SecretResolver
    >>>
    >>> # Initialize secret store
    >>> secret_store = AWSSecretsManager(region_name='us-east-1')
    >>>
    >>> # Use with Config
    >>> config = Config(
    ...     env='production',
    ...     secret_resolver=SecretResolver(secret_store)
    ... )
    >>>
    >>> # Secrets are automatically resolved from placeholders like ${secret:db/password}
    >>> db_password = config.database.password
"""

from config_stash.secret_stores.base import SecretStore
from config_stash.secret_stores.resolver import SecretResolver

# Import providers with optional dependencies
try:
    from config_stash.secret_stores.providers.aws_secrets_manager import AWSSecretsManager
except ImportError:
    AWSSecretsManager = None

try:
    from config_stash.secret_stores.providers.azure_key_vault import AzureKeyVault
except ImportError:
    AzureKeyVault = None

try:
    from config_stash.secret_stores.providers.gcp_secret_manager import GCPSecretManager
except ImportError:
    GCPSecretManager = None

try:
    from config_stash.secret_stores.providers.hashicorp_vault import HashiCorpVault
except ImportError:
    HashiCorpVault = None

try:
    from config_stash.secret_stores.providers.env_secret_store import EnvSecretStore
except ImportError:
    EnvSecretStore = None

# Import utilities
from config_stash.secret_stores.providers.dict_secret_store import DictSecretStore
from config_stash.secret_stores.providers.multi_secret_store import MultiSecretStore

__all__ = [
    "SecretStore",
    "SecretResolver",
    "AWSSecretsManager",
    "AzureKeyVault",
    "GCPSecretManager",
    "HashiCorpVault",
    "EnvSecretStore",
    "DictSecretStore",
    "MultiSecretStore",
]
