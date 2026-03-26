# pyright: basic
"""Tests for the secret_factory module."""

import os
from unittest.mock import MagicMock, patch

import pytest

from config_stash.exceptions import ConfigStashError
from config_stash.secret_factory import (
    _create_secret_store,
    _create_vault_auth,
    create_secret_resolver_from_config,
)
from config_stash.secret_stores.providers.dict_secret_store import DictSecretStore
from config_stash.secret_stores.providers.multi_secret_store import MultiSecretStore
from config_stash.secret_stores.resolver import SecretResolver

# ---------------------------------------------------------------------------
# Vault auth method dispatch
# ---------------------------------------------------------------------------


class TestCreateVaultAuth:
    """Tests for _create_vault_auth."""

    def test_token_returns_string(self):
        result = _create_vault_auth({"method": "token", "token": "s.abc123"})
        assert result == "s.abc123"

    def test_token_missing_raises(self):
        with pytest.raises(ConfigStashError, match="token"):
            _create_vault_auth({"method": "token"})

    def test_approle(self):
        with patch(
            "config_stash.secret_factory.AppRoleAuth",
            create=True,
        ) as mock_cls:
            from config_stash.secret_stores.vault_auth.approle import AppRoleAuth

            result = _create_vault_auth(
                {
                    "method": "approle",
                    "role_id": "r1",
                    "secret_id": "s1",
                    "mount_point": "custom-approle",
                }
            )
            assert isinstance(result, AppRoleAuth)
            assert result.role_id == "r1"
            assert result.secret_id == "s1"
            assert result.mount_point_value == "custom-approle"

    def test_approle_default_mount(self):
        from config_stash.secret_stores.vault_auth.approle import AppRoleAuth

        result = _create_vault_auth(
            {"method": "approle", "role_id": "r1", "secret_id": "s1"}
        )
        assert isinstance(result, AppRoleAuth)
        assert result.mount_point_value == "approle"

    def test_oidc(self):
        from config_stash.secret_stores.vault_auth.oidc import OIDCAuth

        result = _create_vault_auth(
            {"method": "oidc", "role": "my-role", "use_kerberos": True}
        )
        assert isinstance(result, OIDCAuth)
        assert result.role == "my-role"
        assert result.use_kerberos is True
        assert result.mount_point_value == "oidc"

    def test_ldap(self):
        from config_stash.secret_stores.vault_auth.ldap import LDAPAuth

        result = _create_vault_auth(
            {"method": "ldap", "username": "admin", "password": "secret"}
        )
        assert isinstance(result, LDAPAuth)
        assert result.username == "admin"
        assert result.password == "secret"
        assert result.mount_point_value == "ldap"

    def test_jwt(self):
        from config_stash.secret_stores.vault_auth.jwt import JWTAuth

        result = _create_vault_auth({"method": "jwt", "role": "r1", "jwt": "eyJ..."})
        assert isinstance(result, JWTAuth)
        assert result.role == "r1"
        assert result.jwt == "eyJ..."

    def test_kubernetes(self):
        from config_stash.secret_stores.vault_auth.kubernetes import KubernetesAuth

        result = _create_vault_auth({"method": "kubernetes", "role": "k8s-role"})
        assert isinstance(result, KubernetesAuth)
        assert result.role == "k8s-role"
        assert result.mount_point_value == "kubernetes"

    def test_aws(self):
        from config_stash.secret_stores.vault_auth.aws import AWSAuth

        result = _create_vault_auth({"method": "aws", "role": "aws-role"})
        assert isinstance(result, AWSAuth)
        assert result.role == "aws-role"
        assert result.mount_point_value == "aws"

    def test_azure(self):
        from config_stash.secret_stores.vault_auth.azure import AzureAuth

        result = _create_vault_auth(
            {"method": "azure", "role": "az-role", "mount_point": "az-custom"}
        )
        assert isinstance(result, AzureAuth)
        assert result.role == "az-role"
        assert result.mount_point_value == "az-custom"

    def test_gcp(self):
        from config_stash.secret_stores.vault_auth.gcp import GCPAuth

        result = _create_vault_auth({"method": "gcp", "role": "gcp-role"})
        assert isinstance(result, GCPAuth)
        assert result.role == "gcp-role"
        assert result.mount_point_value == "gcp"

    def test_unknown_method_raises(self):
        with pytest.raises(ConfigStashError, match="Unknown vault auth method"):
            _create_vault_auth({"method": "magic"})

    def test_env_var_expansion(self, monkeypatch):
        monkeypatch.setenv("VAULT_TOKEN", "s.from-env")
        result = _create_vault_auth({"method": "token", "token": "${VAULT_TOKEN}"})
        assert result == "s.from-env"


# ---------------------------------------------------------------------------
# Secret store creation
# ---------------------------------------------------------------------------


class TestCreateSecretStore:
    """Tests for _create_secret_store."""

    def test_dict_provider(self):
        store = _create_secret_store({"provider": "dict", "values": {"key1": "val1"}})
        assert isinstance(store, DictSecretStore)
        assert store.get_secret("key1") == "val1"

    def test_dict_provider_empty_values(self):
        store = _create_secret_store({"provider": "dict"})
        assert isinstance(store, DictSecretStore)
        assert store.list_secrets() == []

    def test_env_provider(self, monkeypatch):
        monkeypatch.setenv("TEST_SECRET", "hello")
        from config_stash.secret_stores.providers.env_secret_store import EnvSecretStore

        store = _create_secret_store(
            {"provider": "env", "prefix": "TEST_", "transform_key": False}
        )
        assert isinstance(store, EnvSecretStore)
        assert store.prefix == "TEST_"
        assert store.transform_key is False

    @patch(
        "config_stash.secret_stores.providers.aws_secrets_manager.BOTO3_AVAILABLE",
        True,
    )
    @patch(
        "config_stash.secret_stores.providers.aws_secrets_manager.boto3",
        create=True,
    )
    def test_aws_secrets_manager_provider(self, mock_boto3):
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        store = _create_secret_store(
            {
                "provider": "aws_secrets_manager",
                "region_name": "eu-west-1",
                "endpoint_url": "http://localhost:4566",
            }
        )
        from config_stash.secret_stores.providers.aws_secrets_manager import (
            AWSSecretsManager,
        )

        assert isinstance(store, AWSSecretsManager)
        assert store.region_name == "eu-west-1"

    @patch("config_stash.secret_stores.providers.hashicorp_vault.HVAC_AVAILABLE", True)
    @patch("config_stash.secret_stores.providers.hashicorp_vault.hvac", create=True)
    def test_vault_provider_with_token(self, mock_hvac):
        mock_client = MagicMock()
        mock_client.is_authenticated.return_value = True
        mock_hvac.Client.return_value = mock_client

        store = _create_secret_store(
            {
                "provider": "vault",
                "url": "https://vault.example.com",
                "auth": {"method": "token", "token": "s.test123"},
                "mount_point": "kv",
                "kv_version": 2,
            }
        )
        from config_stash.secret_stores.providers.hashicorp_vault import HashiCorpVault

        assert isinstance(store, HashiCorpVault)
        assert store.url == "https://vault.example.com"
        assert store.mount_point == "kv"

    @patch("config_stash.secret_stores.providers.hashicorp_vault.HVAC_AVAILABLE", True)
    @patch("config_stash.secret_stores.providers.hashicorp_vault.hvac", create=True)
    def test_vault_provider_with_approle(self, mock_hvac):
        mock_client = MagicMock()
        mock_client.is_authenticated.return_value = True
        mock_hvac.Client.return_value = mock_client

        store = _create_secret_store(
            {
                "provider": "vault",
                "url": "https://vault.example.com",
                "auth": {
                    "method": "approle",
                    "role_id": "rid",
                    "secret_id": "sid",
                },
            }
        )
        from config_stash.secret_stores.providers.hashicorp_vault import HashiCorpVault

        assert isinstance(store, HashiCorpVault)

    @patch("config_stash.secret_stores.providers.azure_key_vault.AZURE_AVAILABLE", True)
    @patch(
        "config_stash.secret_stores.providers.azure_key_vault.SecretClient",
        create=True,
    )
    @patch(
        "config_stash.secret_stores.providers.azure_key_vault.DefaultAzureCredential",
        create=True,
    )
    def test_azure_key_vault_provider(self, mock_cred, mock_client_cls):
        mock_cred.return_value = MagicMock()
        mock_client_cls.return_value = MagicMock()
        store = _create_secret_store(
            {
                "provider": "azure_key_vault",
                "vault_url": "https://my-vault.vault.azure.net",
            }
        )
        from config_stash.secret_stores.providers.azure_key_vault import AzureKeyVault

        assert isinstance(store, AzureKeyVault)
        assert store.vault_url == "https://my-vault.vault.azure.net"

    @patch(
        "config_stash.secret_stores.providers.gcp_secret_manager.GCP_AVAILABLE", True
    )
    @patch(
        "config_stash.secret_stores.providers.gcp_secret_manager.secretmanager",
        create=True,
    )
    def test_gcp_secret_manager_provider(self, mock_sm):
        mock_sm.SecretManagerServiceClient.return_value = MagicMock()
        store = _create_secret_store(
            {"provider": "gcp_secret_manager", "project_id": "my-proj"}
        )
        from config_stash.secret_stores.providers.gcp_secret_manager import (
            GCPSecretManager,
        )

        assert isinstance(store, GCPSecretManager)
        assert store.project_id == "my-proj"

    def test_multi_provider(self):
        store = _create_secret_store(
            {
                "provider": "multi",
                "stores": [
                    {"provider": "dict", "values": {"a": "1"}},
                    {"provider": "dict", "values": {"b": "2"}},
                ],
            }
        )
        assert isinstance(store, MultiSecretStore)
        assert len(store.stores) == 2
        # First store has "a", second has "b"
        assert store.get_secret("a") == "1"
        assert store.get_secret("b") == "2"

    def test_multi_provider_empty_stores_raises(self):
        with pytest.raises(ConfigStashError, match="at least one store"):
            _create_secret_store({"provider": "multi", "stores": []})

    def test_multi_provider_recursive_nesting(self):
        store = _create_secret_store(
            {
                "provider": "multi",
                "stores": [
                    {
                        "provider": "multi",
                        "stores": [
                            {"provider": "dict", "values": {"deep": "value"}},
                        ],
                    },
                ],
            }
        )
        assert isinstance(store, MultiSecretStore)
        inner = store.stores[0]
        assert isinstance(inner, MultiSecretStore)
        assert inner.get_secret("deep") == "value"

    def test_unknown_provider_raises(self):
        with pytest.raises(ConfigStashError, match="Unknown secret store provider"):
            _create_secret_store({"provider": "redis"})

    def test_env_var_expansion_in_store(self, monkeypatch):
        monkeypatch.setenv("MY_SECRET_VAL", "expanded")
        store = _create_secret_store(
            {"provider": "dict", "values": {"k": "${MY_SECRET_VAL}"}}
        )
        assert isinstance(store, DictSecretStore)
        assert store.get_secret("k") == "expanded"


# ---------------------------------------------------------------------------
# SecretResolver wrapping
# ---------------------------------------------------------------------------


class TestCreateSecretResolverFromConfig:
    """Tests for create_secret_resolver_from_config."""

    def test_basic_resolver(self):
        resolver = create_secret_resolver_from_config(
            {
                "store": {"provider": "dict", "values": {"x": "1"}},
                "cache_enabled": False,
                "cache_ttl": 60.0,
                "fail_on_missing": False,
                "prefix": "prod/",
            }
        )
        assert isinstance(resolver, SecretResolver)
        assert isinstance(resolver.secret_store, DictSecretStore)
        assert resolver.cache_enabled is False
        assert resolver.cache_ttl == 60.0
        assert resolver.fail_on_missing is False
        assert resolver.prefix == "prod/"

    def test_resolver_defaults(self):
        resolver = create_secret_resolver_from_config(
            {"store": {"provider": "dict", "values": {}}}
        )
        assert resolver.cache_enabled is True
        assert resolver.cache_ttl is None
        assert resolver.fail_on_missing is True
        assert resolver.prefix is None

    def test_resolver_with_provider_at_top_level(self):
        """When 'provider' lives at the top level instead of under 'store'."""
        resolver = create_secret_resolver_from_config(
            {"provider": "dict", "values": {"a": "b"}}
        )
        assert isinstance(resolver, SecretResolver)
        assert isinstance(resolver.secret_store, DictSecretStore)

    def test_missing_store_raises(self):
        with pytest.raises(ConfigStashError, match="store"):
            create_secret_resolver_from_config({"cache_enabled": True})

    def test_env_var_expansion_in_resolver_config(self, monkeypatch):
        monkeypatch.setenv("CACHE_PREFIX", "staging/")
        resolver = create_secret_resolver_from_config(
            {
                "store": {"provider": "dict", "values": {}},
                "prefix": "${CACHE_PREFIX}",
            }
        )
        assert resolver.prefix == "staging/"

    def test_resolver_resolves_secrets(self):
        resolver = create_secret_resolver_from_config(
            {
                "store": {
                    "provider": "dict",
                    "values": {"db/password": "s3cret"},
                },
            }
        )
        assert resolver.resolve("${secret:db/password}") == "s3cret"
