# pyright: basic
"""Tests for config_stash.source_factory module."""

import os
from unittest.mock import patch

import pytest

from config_stash.exceptions import ConfigStashError
from config_stash.loaders import (
    EnvFileLoader,
    EnvironmentLoader,
    IniLoader,
    JsonLoader,
    TomlLoader,
    YamlLoader,
)
from config_stash.loaders.remote_loader import (
    AzureBlobLoader,
    GCPStorageLoader,
    GitLoader,
    HTTPLoader,
    IBMCloudObjectStorageLoader,
    S3Loader,
)
from config_stash.loaders.ssm_loader import SSMLoader
from config_stash.source_factory import (
    _expand_env_vars,
    create_loader_from_config,
    create_loaders_from_config,
)


# ---------------------------------------------------------------------------
# _expand_env_vars
# ---------------------------------------------------------------------------


class TestExpandEnvVars:
    def test_expand_string(self):
        with patch.dict(os.environ, {"MY_VAR": "hello"}):
            assert _expand_env_vars("${MY_VAR}/path") == "hello/path"

    def test_unset_var_left_unchanged(self):
        env = {k: v for k, v in os.environ.items() if k != "NONEXISTENT_VAR_XYZ"}
        with patch.dict(os.environ, env, clear=True):
            assert _expand_env_vars("${NONEXISTENT_VAR_XYZ}") == "${NONEXISTENT_VAR_XYZ}"

    def test_expand_dict_values(self):
        with patch.dict(os.environ, {"DIR": "/tmp"}):
            result = _expand_env_vars({"path": "${DIR}/cfg.yaml", "count": 5})
            assert result == {"path": "/tmp/cfg.yaml", "count": 5}

    def test_expand_list(self):
        with patch.dict(os.environ, {"A": "x", "B": "y"}):
            assert _expand_env_vars(["${A}", "${B}"]) == ["x", "y"]

    def test_non_string_passthrough(self):
        assert _expand_env_vars(42) == 42
        assert _expand_env_vars(None) is None
        assert _expand_env_vars(True) is True

    def test_nested_dict_and_list(self):
        with patch.dict(os.environ, {"V": "val"}):
            result = _expand_env_vars({"a": [{"b": "${V}"}]})
            assert result == {"a": [{"b": "val"}]}


# ---------------------------------------------------------------------------
# create_loader_from_config — file loaders
# ---------------------------------------------------------------------------


class TestFileLoaders:
    def test_yaml_loader(self):
        loader = create_loader_from_config({"type": "yaml", "path": "/etc/app.yaml"})
        assert isinstance(loader, YamlLoader)
        assert loader.source == "/etc/app.yaml"

    def test_json_loader(self):
        loader = create_loader_from_config({"type": "json", "path": "config.json"})
        assert isinstance(loader, JsonLoader)
        assert loader.source == "config.json"

    def test_toml_loader(self):
        loader = create_loader_from_config({"type": "toml", "path": "pyproject.toml"})
        assert isinstance(loader, TomlLoader)
        assert loader.source == "pyproject.toml"

    def test_ini_loader(self):
        loader = create_loader_from_config({"type": "ini", "path": "setup.cfg"})
        assert isinstance(loader, IniLoader)
        assert loader.source == "setup.cfg"

    def test_env_var_expansion_in_path(self):
        with patch.dict(os.environ, {"CFG_DIR": "/opt/configs"}):
            loader = create_loader_from_config(
                {"type": "yaml", "path": "${CFG_DIR}/app.yaml"}
            )
            assert loader.source == "/opt/configs/app.yaml"


# ---------------------------------------------------------------------------
# create_loader_from_config — env loaders
# ---------------------------------------------------------------------------


class TestEnvLoaders:
    def test_env_file_default_path(self):
        loader = create_loader_from_config({"type": "env_file"})
        assert isinstance(loader, EnvFileLoader)
        assert loader.source == ".env"

    def test_env_file_custom_path(self):
        loader = create_loader_from_config({"type": "env_file", "path": ".env.local"})
        assert isinstance(loader, EnvFileLoader)
        assert loader.source == ".env.local"

    def test_environment_loader(self):
        loader = create_loader_from_config(
            {"type": "environment", "prefix": "MYAPP", "separator": "_"}
        )
        assert isinstance(loader, EnvironmentLoader)
        assert loader.prefix == "MYAPP"
        assert loader.separator == "_"

    def test_environment_loader_defaults(self):
        loader = create_loader_from_config(
            {"type": "environment", "prefix": "APP"}
        )
        assert isinstance(loader, EnvironmentLoader)
        assert loader.separator == "__"


# ---------------------------------------------------------------------------
# create_loader_from_config — SSM
# ---------------------------------------------------------------------------


class TestSSMLoader:
    def test_ssm_loader(self):
        loader = create_loader_from_config(
            {
                "type": "ssm",
                "path_prefix": "/myapp/prod/",
                "decrypt": False,
                "aws_region": "eu-west-1",
                "aws_access_key_id": "AKIA_FAKE",
                "aws_secret_access_key": "secret",
            }
        )
        assert isinstance(loader, SSMLoader)
        assert loader.path_prefix == "/myapp/prod/"
        assert loader.decrypt is False
        assert loader.aws_region == "eu-west-1"
        assert loader.aws_access_key_id == "AKIA_FAKE"
        assert loader.aws_secret_access_key == "secret"


# ---------------------------------------------------------------------------
# create_loader_from_config — HTTP
# ---------------------------------------------------------------------------


class TestHTTPLoader:
    @patch("config_stash.loaders.remote_loader.HAS_REQUESTS", True)
    @patch("config_stash.loaders.remote_loader.requests", create=True)
    def test_http_loader(self, _mock_requests):
        loader = create_loader_from_config(
            {
                "type": "http",
                "url": "https://example.com/config.yaml",
                "timeout": 10,
                "headers": {"X-API-Key": "abc123"},
                "auth": ["user", "pass"],
            }
        )
        assert isinstance(loader, HTTPLoader)
        assert loader.url == "https://example.com/config.yaml"
        assert loader.timeout == 10
        assert loader.headers == {"X-API-Key": "abc123"}
        assert loader.auth == ("user", "pass")

    @patch("config_stash.loaders.remote_loader.HAS_REQUESTS", True)
    @patch("config_stash.loaders.remote_loader.requests", create=True)
    def test_http_loader_env_var_in_headers(self, _mock_requests):
        with patch.dict(os.environ, {"API_KEY": "secret_key"}):
            loader = create_loader_from_config(
                {
                    "type": "http",
                    "url": "https://example.com/config.yaml",
                    "headers": {"Authorization": "Bearer ${API_KEY}"},
                }
            )
            assert loader.headers == {"Authorization": "Bearer secret_key"}

    @patch("config_stash.loaders.remote_loader.HAS_REQUESTS", True)
    @patch("config_stash.loaders.remote_loader.requests", create=True)
    def test_http_loader_no_auth(self, _mock_requests):
        loader = create_loader_from_config(
            {"type": "http", "url": "https://example.com/config.yaml"}
        )
        assert loader.auth is None


# ---------------------------------------------------------------------------
# create_loader_from_config — S3
# ---------------------------------------------------------------------------


class TestS3Loader:
    def test_s3_loader(self):
        loader = create_loader_from_config(
            {
                "type": "s3",
                "url": "s3://my-bucket/config.yaml",
                "aws_access_key": "AKID",
                "aws_secret_key": "SKEY",
                "region": "us-west-2",
            }
        )
        assert isinstance(loader, S3Loader)
        assert loader.bucket == "my-bucket"
        assert loader.key == "config.yaml"
        assert loader.aws_access_key == "AKID"
        assert loader.aws_secret_key == "SKEY"
        assert loader.region == "us-west-2"

    def test_s3_loader_defaults(self):
        loader = create_loader_from_config(
            {"type": "s3", "url": "s3://bucket/path/file.json"}
        )
        assert isinstance(loader, S3Loader)
        assert loader.region == "us-east-1"


# ---------------------------------------------------------------------------
# create_loader_from_config — Azure Blob
# ---------------------------------------------------------------------------


class TestAzureBlobLoader:
    def test_azure_blob_loader(self):
        loader = create_loader_from_config(
            {
                "type": "azure_blob",
                "container": "my-container",
                "blob": "config.yaml",
                "account_name": "myaccount",
                "account_key": "mykey",
            }
        )
        assert isinstance(loader, AzureBlobLoader)
        assert loader.container_url == "my-container"
        assert loader.blob_name == "config.yaml"
        assert loader.account_name == "myaccount"
        assert loader.account_key == "mykey"


# ---------------------------------------------------------------------------
# create_loader_from_config — GCP Storage
# ---------------------------------------------------------------------------


class TestGCPStorageLoader:
    def test_gcp_storage_loader(self):
        loader = create_loader_from_config(
            {
                "type": "gcp_storage",
                "bucket": "my-gcp-bucket",
                "blob": "app/config.yaml",
                "project_id": "my-project",
                "credentials_path": "/creds/sa.json",
            }
        )
        assert isinstance(loader, GCPStorageLoader)
        assert loader.bucket_name == "my-gcp-bucket"
        assert loader.blob_name == "app/config.yaml"
        assert loader.project_id == "my-project"
        assert loader.credentials_path == "/creds/sa.json"


# ---------------------------------------------------------------------------
# create_loader_from_config — IBM COS
# ---------------------------------------------------------------------------


class TestIBMCOSLoader:
    def test_ibm_cos_loader(self):
        loader = create_loader_from_config(
            {
                "type": "ibm_cos",
                "bucket": "ibm-bucket",
                "key": "config.yaml",
                "api_key": "ibm-api-key",
                "service_instance_id": "crn:v1:...",
                "region": "eu-de",
            }
        )
        assert isinstance(loader, IBMCloudObjectStorageLoader)
        assert loader.bucket_name == "ibm-bucket"
        assert loader.object_key == "config.yaml"
        assert loader.api_key == "ibm-api-key"
        assert loader.service_instance_id == "crn:v1:..."
        assert loader.region == "eu-de"

    def test_ibm_cos_loader_defaults(self):
        loader = create_loader_from_config(
            {"type": "ibm_cos", "bucket": "b", "key": "k.yaml"}
        )
        assert loader.region == "us-south"


# ---------------------------------------------------------------------------
# create_loader_from_config — Git
# ---------------------------------------------------------------------------


class TestGitLoader:
    def test_git_loader(self):
        loader = create_loader_from_config(
            {
                "type": "git",
                "repo": "https://github.com/org/repo",
                "file_path": "config/app.yaml",
                "branch": "develop",
                "token": "ghp_fake",
            }
        )
        assert isinstance(loader, GitLoader)
        assert loader.url == "https://github.com/org/repo"
        assert loader.file_path == "config/app.yaml"
        assert loader.branch == "develop"
        assert loader.token == "ghp_fake"

    def test_git_loader_defaults(self):
        loader = create_loader_from_config(
            {
                "type": "git",
                "repo": "https://github.com/org/repo",
                "file_path": "config.yaml",
            }
        )
        assert loader.branch == "main"


# ---------------------------------------------------------------------------
# create_loader_from_config — custom
# ---------------------------------------------------------------------------


class TestCustomLoader:
    def test_custom_loader_dynamic_import(self):
        loader = create_loader_from_config(
            {
                "type": "custom",
                "class": "config_stash.loaders.yaml_loader.YamlLoader",
                "args": {"source": "/custom/path.yaml"},
            }
        )
        assert isinstance(loader, YamlLoader)
        assert loader.source == "/custom/path.yaml"

    def test_custom_loader_no_args(self):
        loader = create_loader_from_config(
            {
                "type": "custom",
                "class": "config_stash.loaders.env_file_loader.EnvFileLoader",
                "args": {"source": ".env.custom"},
            }
        )
        assert isinstance(loader, EnvFileLoader)
        assert loader.source == ".env.custom"


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


class TestErrorCases:
    def test_unknown_type_raises_error(self):
        with pytest.raises(ConfigStashError, match="Unknown source type: 'foobar'"):
            create_loader_from_config({"type": "foobar"})

    def test_missing_type_raises_error(self):
        with pytest.raises(ConfigStashError, match="must include a 'type' key"):
            create_loader_from_config({"path": "/some/file.yaml"})


# ---------------------------------------------------------------------------
# create_loaders_from_config — multiple sources
# ---------------------------------------------------------------------------


class TestCreateLoadersFromConfig:
    def test_order_preserved(self):
        sources = [
            {"type": "yaml", "path": "base.yaml"},
            {"type": "json", "path": "override.json"},
            {"type": "env_file"},
        ]
        loaders = create_loaders_from_config(sources)
        assert len(loaders) == 3
        assert isinstance(loaders[0], YamlLoader)
        assert isinstance(loaders[1], JsonLoader)
        assert isinstance(loaders[2], EnvFileLoader)
        assert loaders[0].source == "base.yaml"
        assert loaders[1].source == "override.json"

    def test_empty_list(self):
        assert create_loaders_from_config([]) == []

    @patch("config_stash.loaders.remote_loader.HAS_REQUESTS", True)
    @patch("config_stash.loaders.remote_loader.requests", create=True)
    def test_mixed_loader_types(self, _mock_requests):
        sources = [
            {"type": "yaml", "path": "a.yaml"},
            {"type": "http", "url": "https://cfg.example.com/c.json"},
            {"type": "environment", "prefix": "APP"},
        ]
        loaders = create_loaders_from_config(sources)
        assert isinstance(loaders[0], YamlLoader)
        assert isinstance(loaders[1], HTTPLoader)
        assert isinstance(loaders[2], EnvironmentLoader)
