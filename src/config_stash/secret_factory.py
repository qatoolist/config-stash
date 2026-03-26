"""Factory module for creating SecretResolver instances from declarative config dicts.

This module provides functions to create secret store and resolver instances
from simple dictionary definitions, enabling declarative configuration of
secret management.
"""

from typing import Any, Dict, Optional

from config_stash.exceptions import ConfigStashError
from config_stash.secret_stores.base import SecretStore
from config_stash.secret_stores.providers.dict_secret_store import DictSecretStore
from config_stash.secret_stores.providers.multi_secret_store import MultiSecretStore
from config_stash.secret_stores.resolver import SecretResolver
from config_stash.source_factory import _expand_env_vars


def _create_vault_auth(auth_dict: Dict[str, Any]) -> Any:
    """Map an auth configuration dict to the appropriate VaultAuthMethod instance.

    Args:
        auth_dict: Dictionary containing at least a ``method`` key that selects
            the authentication backend, plus any parameters required by that
            backend.

    Returns:
        A ``VaultAuthMethod`` instance (or the raw token string when
        ``method`` is ``"token"``).

    Raises:
        ConfigStashError: If the method is unknown or required parameters are
            missing.
    """
    expanded: Dict[str, Any] = _expand_env_vars(auth_dict)
    method = expanded.get("method")

    if method == "token":
        # Token auth is handled directly by HashiCorpVault — just return
        # the token string so the caller can pass it as ``token=``.
        token = expanded.get("token")
        if not token:
            raise ConfigStashError(
                "Vault token auth requires a 'token' field",
                context={"auth": expanded},
            )
        return token

    if method == "approle":
        from config_stash.secret_stores.vault_auth.approle import AppRoleAuth

        return AppRoleAuth(
            role_id=expanded["role_id"],
            secret_id=expanded["secret_id"],
            mount_point=expanded.get("mount_point", "approle"),
        )

    if method == "oidc":
        from config_stash.secret_stores.vault_auth.oidc import OIDCAuth

        return OIDCAuth(
            role=expanded["role"],
            use_kerberos=expanded.get("use_kerberos", False),
            mount_point=expanded.get("mount_point", "oidc"),
        )

    if method == "ldap":
        from config_stash.secret_stores.vault_auth.ldap import LDAPAuth

        return LDAPAuth(
            username=expanded["username"],
            password=expanded.get("password"),
            mount_point=expanded.get("mount_point", "ldap"),
        )

    if method == "jwt":
        from config_stash.secret_stores.vault_auth.jwt import JWTAuth

        return JWTAuth(
            role=expanded["role"],
            jwt=expanded["jwt"],
            mount_point=expanded.get("mount_point", "jwt"),
        )

    if method == "kubernetes":
        from config_stash.secret_stores.vault_auth.kubernetes import KubernetesAuth

        return KubernetesAuth(
            role=expanded["role"],
            mount_point=expanded.get("mount_point", "kubernetes"),
        )

    if method == "aws":
        from config_stash.secret_stores.vault_auth.aws import AWSAuth

        return AWSAuth(
            role=expanded["role"],
            mount_point=expanded.get("mount_point", "aws"),
        )

    if method == "azure":
        from config_stash.secret_stores.vault_auth.azure import AzureAuth

        return AzureAuth(
            role=expanded["role"],
            mount_point=expanded.get("mount_point", "azure"),
        )

    if method == "gcp":
        from config_stash.secret_stores.vault_auth.gcp import GCPAuth

        return GCPAuth(
            role=expanded["role"],
            mount_point=expanded.get("mount_point", "gcp"),
        )

    raise ConfigStashError(
        f"Unknown vault auth method: {method!r}",
        context={"auth": expanded},
    )


def _create_secret_store(config_dict: Dict[str, Any]) -> SecretStore:
    """Map a config dict to a SecretStore instance.

    The dict must contain a ``provider`` key that selects the backend.
    All remaining keys are forwarded as constructor arguments (after
    env-var expansion).

    Args:
        config_dict: Provider configuration dictionary.

    Returns:
        A concrete ``SecretStore`` instance.

    Raises:
        ConfigStashError: If the provider is unknown or required parameters
            are missing.
    """
    expanded: Dict[str, Any] = _expand_env_vars(config_dict)
    provider = expanded.get("provider")

    if provider == "aws_secrets_manager":
        from config_stash.secret_stores.providers.aws_secrets_manager import (
            AWSSecretsManager,
        )

        return AWSSecretsManager(
            region_name=expanded.get("region_name", "us-east-1"),
            aws_access_key_id=expanded.get("aws_access_key_id"),
            aws_secret_access_key=expanded.get("aws_secret_access_key"),
            aws_session_token=expanded.get("aws_session_token"),
            endpoint_url=expanded.get("endpoint_url"),
        )

    if provider == "vault":
        from config_stash.secret_stores.providers.hashicorp_vault import HashiCorpVault

        auth_cfg = expanded.get("auth", {})
        auth_result = _create_vault_auth(auth_cfg) if auth_cfg else None

        # When the auth method is "token", _create_vault_auth returns the
        # raw token string rather than a VaultAuthMethod instance.
        token: Optional[str] = None
        auth_method: Any = None
        if isinstance(auth_result, str):
            token = auth_result
        else:
            auth_method = auth_result

        return HashiCorpVault(
            url=expanded.get("url", "http://127.0.0.1:8200"),
            token=token,
            auth_method=auth_method,
            namespace=expanded.get("namespace"),
            mount_point=expanded.get("mount_point", "secret"),
            kv_version=expanded.get("kv_version", 2),
            verify=expanded.get("verify", True),
        )

    if provider == "azure_key_vault":
        from config_stash.secret_stores.providers.azure_key_vault import AzureKeyVault

        return AzureKeyVault(
            vault_url=expanded["vault_url"],
        )

    if provider == "gcp_secret_manager":
        from config_stash.secret_stores.providers.gcp_secret_manager import (
            GCPSecretManager,
        )

        return GCPSecretManager(
            project_id=expanded["project_id"],
        )

    if provider == "env":
        from config_stash.secret_stores.providers.env_secret_store import EnvSecretStore

        return EnvSecretStore(
            prefix=expanded.get("prefix", ""),
            suffix=expanded.get("suffix", ""),
            transform_key=expanded.get("transform_key", True),
            case_sensitive=expanded.get("case_sensitive", False),
        )

    if provider == "dict":
        return DictSecretStore(
            secrets=expanded.get("values") or {},
        )

    if provider == "multi":
        stores_cfg = expanded.get("stores", [])
        if not stores_cfg:
            raise ConfigStashError(
                "MultiSecretStore requires at least one store in 'stores'",
                context={"provider": provider},
            )
        child_stores = [_create_secret_store(s) for s in stores_cfg]
        return MultiSecretStore(stores=child_stores)

    raise ConfigStashError(
        f"Unknown secret store provider: {provider!r}",
        context={"config": expanded},
    )


def create_secret_resolver_from_config(
    secrets_dict: Dict[str, Any],
) -> SecretResolver:
    """Create a fully-configured SecretResolver from a declarative dict.

    The dictionary must contain at least the store configuration (a nested
    dict with a ``provider`` key).  Additional top-level keys control the
    resolver behaviour:

    * ``cache_enabled`` (bool, default ``True``)
    * ``cache_ttl`` (float | None, default ``None``)
    * ``fail_on_missing`` (bool, default ``True``)
    * ``prefix`` (str | None, default ``None``)

    Args:
        secrets_dict: Top-level secrets configuration.  Must include a
            ``store`` (or ``provider``) sub-dict.

    Returns:
        A ``SecretResolver`` wrapping the constructed store.

    Raises:
        ConfigStashError: If required configuration is missing or invalid.
    """
    expanded: Dict[str, Any] = _expand_env_vars(secrets_dict)

    # The store config can live under "store" or at the top level when
    # "provider" is present directly.
    store_cfg = expanded.get("store")
    if store_cfg is None and "provider" in expanded:
        store_cfg = expanded
    if store_cfg is None:
        raise ConfigStashError(
            "Secret resolver config requires a 'store' dict with a 'provider' key",
            context={"config": expanded},
        )

    store = _create_secret_store(store_cfg)

    return SecretResolver(
        secret_store=store,
        cache_enabled=expanded.get("cache_enabled", True),
        cache_ttl=expanded.get("cache_ttl"),
        fail_on_missing=expanded.get("fail_on_missing", True),
        prefix=expanded.get("prefix"),
    )
