"""Tests for SSMLoader — AWS Systems Manager Parameter Store loader."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from config_stash.loaders.ssm_loader import SSMLoader


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_parameter(name: str, value: str, param_type: str = "String"):
    """Build a single SSM parameter dict as returned by the API."""
    return {"Name": name, "Value": value, "Type": param_type}


def _make_paginator(pages):
    """Return a mock paginator whose .paginate() yields *pages*.

    Each element in *pages* is a list of parameter dicts.
    """
    paginator = MagicMock()
    paginator.paginate.return_value = [
        {"Parameters": page} for page in pages
    ]
    return paginator


def _mock_boto3_with_paginator(pages):
    """Create a mock boto3 module with an SSM client returning given pages."""
    mock_boto3 = MagicMock()
    mock_client = MagicMock()
    mock_client.get_paginator.return_value = _make_paginator(pages)
    mock_boto3.client.return_value = mock_client
    return mock_boto3, mock_client


@pytest.fixture()
def boto3_mock():
    """Fixture that injects a mock boto3 into sys.modules for the duration of a test."""
    mock_boto3 = MagicMock()
    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client

    with patch.dict(sys.modules, {"boto3": mock_boto3}):
        yield mock_boto3, mock_client


# ---------------------------------------------------------------------------
# Basic loading & path-to-nested-dict conversion
# ---------------------------------------------------------------------------

class TestSSMLoaderBasic:
    """Basic parameter loading and path conversion."""

    def test_basic_loading(self):
        """Parameters under prefix are converted to nested dict."""
        params = [
            _make_parameter("/app/prod/database/host", "db.example.com"),
            _make_parameter("/app/prod/database/port", "5432"),
            _make_parameter("/app/prod/app_name", "my-service"),
        ]
        mock_boto3, mock_client = _mock_boto3_with_paginator([params])

        loader = SSMLoader(path_prefix="/app/prod/")

        with patch.dict(sys.modules, {"boto3": mock_boto3}):
            result = loader.load()

        assert result is not None
        assert result["database"]["host"] == "db.example.com"
        assert result["database"]["port"] == 5432  # coerced to int
        assert result["app_name"] == "my-service"

    def test_trailing_slash_added_automatically(self):
        """A missing trailing slash on path_prefix is added."""
        loader = SSMLoader(path_prefix="/app/prod")
        assert loader.path_prefix == "/app/prod/"

    def test_trailing_slash_preserved(self):
        """An existing trailing slash is not doubled."""
        loader = SSMLoader(path_prefix="/app/prod/")
        assert loader.path_prefix == "/app/prod/"

    def test_deeply_nested_keys(self):
        """Multi-level nesting works correctly."""
        params = [
            _make_parameter("/app/a/b/c/d", "deep"),
        ]
        mock_boto3, _ = _mock_boto3_with_paginator([params])
        loader = SSMLoader(path_prefix="/app/")

        with patch.dict(sys.modules, {"boto3": mock_boto3}):
            result = loader.load()

        assert result == {"a": {"b": {"c": {"d": "deep"}}}}


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

class TestSSMLoaderPagination:
    """Pagination handling across multiple API pages."""

    def test_pagination_merges_all_pages(self):
        """Parameters from multiple pages are merged into one dict."""
        page1 = [
            _make_parameter("/app/database/host", "db.example.com"),
        ]
        page2 = [
            _make_parameter("/app/database/port", "5432"),
        ]
        page3 = [
            _make_parameter("/app/cache/backend", "redis"),
        ]

        mock_boto3, _ = _mock_boto3_with_paginator([page1, page2, page3])
        loader = SSMLoader(path_prefix="/app/")

        with patch.dict(sys.modules, {"boto3": mock_boto3}):
            result = loader.load()

        assert result is not None
        assert result["database"]["host"] == "db.example.com"
        assert result["database"]["port"] == 5432
        assert result["cache"]["backend"] == "redis"


# ---------------------------------------------------------------------------
# SecureString / decrypt
# ---------------------------------------------------------------------------

class TestSSMLoaderDecrypt:
    """SecureString decryption support."""

    def test_decrypt_true_passed_to_api(self):
        """WithDecryption=True is forwarded when decrypt=True."""
        mock_boto3, mock_client = _mock_boto3_with_paginator([[]])
        loader = SSMLoader(path_prefix="/app/", decrypt=True)

        with patch.dict(sys.modules, {"boto3": mock_boto3}):
            loader.load()

        mock_client.get_paginator.return_value.paginate.assert_called_once_with(
            Path="/app/",
            Recursive=True,
            WithDecryption=True,
        )

    def test_decrypt_false_passed_to_api(self):
        """WithDecryption=False is forwarded when decrypt=False."""
        mock_boto3, mock_client = _mock_boto3_with_paginator([[]])
        loader = SSMLoader(path_prefix="/app/", decrypt=False)

        with patch.dict(sys.modules, {"boto3": mock_boto3}):
            loader.load()

        mock_client.get_paginator.return_value.paginate.assert_called_once_with(
            Path="/app/",
            Recursive=True,
            WithDecryption=False,
        )

    def test_secure_string_values_loaded(self):
        """SecureString parameters are loaded and coerced like any other."""
        params = [
            _make_parameter("/app/db_password", "s3cret!", "SecureString"),
            _make_parameter("/app/api_key", "abc123", "SecureString"),
        ]
        mock_boto3, _ = _mock_boto3_with_paginator([params])
        loader = SSMLoader(path_prefix="/app/", decrypt=True)

        with patch.dict(sys.modules, {"boto3": mock_boto3}):
            result = loader.load()

        assert result is not None
        assert result["db_password"] == "s3cret!"
        assert result["api_key"] == "abc123"


# ---------------------------------------------------------------------------
# Type coercion
# ---------------------------------------------------------------------------

class TestSSMLoaderTypeCoercion:
    """Values are coerced from strings to native Python types."""

    def test_integer_coercion(self):
        params = [_make_parameter("/app/port", "5432")]
        mock_boto3, _ = _mock_boto3_with_paginator([params])
        loader = SSMLoader(path_prefix="/app/")

        with patch.dict(sys.modules, {"boto3": mock_boto3}):
            result = loader.load()

        assert result["port"] == 5432
        assert isinstance(result["port"], int)

    def test_boolean_coercion(self):
        params = [
            _make_parameter("/app/debug", "true"),
            _make_parameter("/app/ssl", "false"),
        ]
        mock_boto3, _ = _mock_boto3_with_paginator([params])
        loader = SSMLoader(path_prefix="/app/")

        with patch.dict(sys.modules, {"boto3": mock_boto3}):
            result = loader.load()

        assert result["debug"] is True
        assert result["ssl"] is False

    def test_float_coercion(self):
        params = [_make_parameter("/app/rate", "3.14")]
        mock_boto3, _ = _mock_boto3_with_paginator([params])
        loader = SSMLoader(path_prefix="/app/")

        with patch.dict(sys.modules, {"boto3": mock_boto3}):
            result = loader.load()

        assert result["rate"] == 3.14
        assert isinstance(result["rate"], float)

    def test_string_preserved(self):
        params = [_make_parameter("/app/name", "my-service")]
        mock_boto3, _ = _mock_boto3_with_paginator([params])
        loader = SSMLoader(path_prefix="/app/")

        with patch.dict(sys.modules, {"boto3": mock_boto3}):
            result = loader.load()

        assert result["name"] == "my-service"
        assert isinstance(result["name"], str)


# ---------------------------------------------------------------------------
# Empty result
# ---------------------------------------------------------------------------

class TestSSMLoaderEmpty:
    """Empty parameter sets return None."""

    def test_empty_result_returns_none(self):
        mock_boto3, _ = _mock_boto3_with_paginator([[]])
        loader = SSMLoader(path_prefix="/app/nonexistent/")

        with patch.dict(sys.modules, {"boto3": mock_boto3}):
            result = loader.load()

        assert result is None


# ---------------------------------------------------------------------------
# ImportError when boto3 is missing
# ---------------------------------------------------------------------------

class TestSSMLoaderImportError:
    """Graceful handling when boto3 is not installed."""

    def test_import_error_raised(self):
        loader = SSMLoader(path_prefix="/app/")

        with patch.dict(sys.modules, {"boto3": None}):
            with pytest.raises(ImportError, match="boto3 is required"):
                loader.load()


# ---------------------------------------------------------------------------
# AWS credentials
# ---------------------------------------------------------------------------

class TestSSMLoaderCredentials:
    """AWS credentials from constructor and environment variable fallbacks."""

    def test_explicit_credentials(self):
        """Explicit credentials are passed to boto3.client."""
        mock_boto3, _ = _mock_boto3_with_paginator([[]])
        loader = SSMLoader(
            path_prefix="/app/",
            aws_region="eu-west-1",
            aws_access_key_id="AKIA_TEST",
            aws_secret_access_key="secret_test",
        )

        with patch.dict(sys.modules, {"boto3": mock_boto3}):
            loader.load()

        mock_boto3.client.assert_called_once_with(
            "ssm",
            region_name="eu-west-1",
            aws_access_key_id="AKIA_TEST",
            aws_secret_access_key="secret_test",
        )

    def test_env_var_fallback_credentials(self):
        """Credentials fall back to environment variables."""
        env_vars = {
            "AWS_ACCESS_KEY_ID": "AKIA_ENV",
            "AWS_SECRET_ACCESS_KEY": "secret_env",
            "AWS_DEFAULT_REGION": "ap-southeast-1",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            loader = SSMLoader(path_prefix="/app/")

        assert loader.aws_access_key_id == "AKIA_ENV"
        assert loader.aws_secret_access_key == "secret_env"
        assert loader.aws_region == "ap-southeast-1"

    def test_default_region_without_env(self):
        """Region defaults to us-east-1 when not set anywhere."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AWS_DEFAULT_REGION", None)
            loader = SSMLoader(path_prefix="/app/")

        assert loader.aws_region == "us-east-1"

    def test_iam_credentials_no_keys(self):
        """When no keys are provided, boto3 uses default credential chain."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AWS_ACCESS_KEY_ID", None)
            os.environ.pop("AWS_SECRET_ACCESS_KEY", None)
            loader = SSMLoader(path_prefix="/app/")

        mock_boto3, _ = _mock_boto3_with_paginator([[]])

        with patch.dict(sys.modules, {"boto3": mock_boto3}):
            loader.load()

        # Should NOT pass access key / secret key kwargs
        mock_boto3.client.assert_called_once_with(
            "ssm",
            region_name="us-east-1",
        )


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestSSMLoaderErrors:
    """ConfigLoadError is raised on API failures."""

    def test_api_error_raises_config_load_error(self):
        from config_stash.exceptions import ConfigLoadError

        mock_boto3 = MagicMock()
        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.side_effect = Exception("Access denied")
        mock_client.get_paginator.return_value = mock_paginator
        mock_boto3.client.return_value = mock_client

        loader = SSMLoader(path_prefix="/app/")

        with patch.dict(sys.modules, {"boto3": mock_boto3}):
            with pytest.raises(ConfigLoadError, match="Failed to load SSM"):
                loader.load()
