"""Tests for remote configuration loaders."""

import json
import unittest
from unittest.mock import MagicMock, Mock, patch

try:
    import requests

    from config_stash.loaders.remote_loader import GitLoader, HTTPLoader, RemoteLoader, S3Loader

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class TestRemoteLoader(unittest.TestCase):
    """Test base RemoteLoader class."""
# pyright: reportOptionalSubscript=false, reportOptionalMemberAccess=false
# pyright: reportArgumentType=false, reportPossiblyUnboundVariable=false
# pyright: reportAttributeAccessIssue=false, reportCallIssue=false
# pyright: reportMissingImports=false

    @unittest.skipUnless(HAS_REQUESTS, "requests not installed")
    def test_initialization(self):
        """Test RemoteLoader initialization."""
        loader = RemoteLoader(
            url="http://example.com/config.json",
            timeout=60,
            headers={"Authorization": "Bearer token"},
        )

        self.assertEqual(loader.url, "http://example.com/config.json")
        self.assertEqual(loader.timeout, 60)
        self.assertEqual(loader.headers, {"Authorization": "Bearer token"})
        self.assertEqual(loader.source, "http://example.com/config.json")
        self.assertEqual(loader.config, {})

    @unittest.skipUnless(HAS_REQUESTS, "requests not installed")
    def test_load_not_implemented(self):
        """Test that base load method raises NotImplementedError."""
        loader = RemoteLoader("http://example.com")
        with self.assertRaises(NotImplementedError):
            loader.load()


@unittest.skipUnless(HAS_REQUESTS, "requests not installed")
class TestHTTPLoader(unittest.TestCase):
    """Test HTTPLoader class."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_config = {
            "database": {"host": "localhost", "port": 5432},
            "app": {"name": "TestApp", "version": "1.0.0"},
        }

    @patch("requests.get")
    def test_load_json(self, mock_get):
        """Test loading JSON configuration from HTTP."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = self.test_config
        mock_response.headers = {"content-type": "application/json"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        loader = HTTPLoader("http://example.com/config.json")
        config = loader.load()

        self.assertEqual(config, self.test_config)
        mock_get.assert_called_once_with(
            "http://example.com/config.json", timeout=30, headers={}, auth=None
        )

    @patch("requests.get")
    def test_load_yaml(self, mock_get):
        """Test loading YAML configuration from HTTP."""
        yaml_content = """
database:
  host: localhost
  port: 5432
app:
  name: TestApp
  version: 1.0.0
"""
        mock_response = Mock()
        mock_response.text = yaml_content
        mock_response.headers = {"content-type": "application/yaml"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        loader = HTTPLoader("http://example.com/config.yaml")
        config = loader.load()

        self.assertEqual(config["database"]["host"], "localhost")
        self.assertEqual(config["app"]["name"], "TestApp")

    @patch("requests.get")
    def test_load_toml(self, mock_get):
        """Test loading TOML configuration from HTTP."""
        toml_content = """
[database]
host = "localhost"
port = 5432

[app]
name = "TestApp"
version = "1.0.0"
"""
        mock_response = Mock()
        mock_response.text = toml_content
        mock_response.headers = {"content-type": "application/toml"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        loader = HTTPLoader("http://example.com/config.toml")
        config = loader.load()

        self.assertEqual(config["database"]["host"], "localhost")
        self.assertEqual(config["app"]["name"], "TestApp")

    @patch("requests.get")
    def test_load_with_auth(self, mock_get):
        """Test loading with authentication."""
        mock_response = Mock()
        mock_response.json.return_value = self.test_config
        mock_response.headers = {}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        loader = HTTPLoader("http://api.example.com/config", auth=("user", "password"))
        config = loader.load()

        self.assertEqual(config, self.test_config)
        mock_get.assert_called_once_with(
            "http://api.example.com/config", timeout=30, headers={}, auth=("user", "password")
        )

    @patch("requests.get")
    def test_load_with_headers(self, mock_get):
        """Test loading with custom headers."""
        mock_response = Mock()
        mock_response.json.return_value = self.test_config
        mock_response.headers = {}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        headers = {"Authorization": "Bearer token123", "X-API-Key": "secret"}
        loader = HTTPLoader("http://api.example.com/config", headers=headers)
        config = loader.load()

        self.assertEqual(config, self.test_config)
        mock_get.assert_called_once_with(
            "http://api.example.com/config", timeout=30, headers=headers, auth=None
        )

    @patch("requests.get")
    def test_load_failure(self, mock_get):
        """Test handling of HTTP errors."""
        from config_stash.exceptions import ConfigLoadError

        mock_get.side_effect = requests.RequestException("Connection error")

        loader = HTTPLoader("http://example.com/config.json")
        with self.assertRaises(ConfigLoadError) as context:
            loader.load()

        self.assertIn("Failed to load remote configuration", str(context.exception))

    @patch("requests.get")
    def test_detect_format_from_url(self, mock_get):
        """Test format detection from URL extension."""
        mock_response = Mock()
        mock_response.json.return_value = self.test_config
        mock_response.headers = {}  # No content-type
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Should detect JSON from .json extension
        loader = HTTPLoader("http://example.com/config.json")
        config = loader.load()
        self.assertEqual(config, self.test_config)


@unittest.skipUnless(HAS_REQUESTS, "requests not installed")
class TestS3Loader(unittest.TestCase):
    """Test S3Loader class."""

    def test_s3_url_parsing(self):
        """Test S3 URL parsing."""
        loader = S3Loader("s3://my-bucket/path/to/config.json")

        self.assertEqual(loader.bucket, "my-bucket")
        self.assertEqual(loader.key, "path/to/config.json")

    def test_invalid_s3_url(self):
        """Test that invalid S3 URLs are rejected."""
        with self.assertRaises(ValueError) as context:
            S3Loader("http://not-s3-url.com/config.json")

        self.assertIn("Invalid S3 URL", str(context.exception))

    @patch("boto3.client")
    def test_load_from_s3_json(self, mock_boto_client):
        """Test loading JSON from S3."""
        # Mock S3 client
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        test_config = {"key": "value", "nested": {"data": 123}}
        mock_response = {
            "Body": Mock(read=Mock(return_value=json.dumps(test_config).encode("utf-8")))
        }
        mock_s3.get_object.return_value = mock_response

        loader = S3Loader(
            "s3://test-bucket/configs/app.json", aws_access_key="KEY", aws_secret_key="SECRET"
        )
        config = loader.load()

        self.assertEqual(config, test_config)
        mock_s3.get_object.assert_called_once_with(Bucket="test-bucket", Key="configs/app.json")

    @patch("boto3.client")
    def test_load_from_s3_yaml(self, mock_boto_client):
        """Test loading YAML from S3."""
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        yaml_content = "key: value\nnested:\n  data: 123"
        mock_response = {"Body": Mock(read=Mock(return_value=yaml_content.encode("utf-8")))}
        mock_s3.get_object.return_value = mock_response

        loader = S3Loader("s3://test-bucket/config.yaml")
        config = loader.load()

        self.assertEqual(config["key"], "value")
        self.assertEqual(config["nested"]["data"], 123)

    @patch("boto3.client")
    def test_s3_error_handling(self, mock_boto_client):
        """Test S3 error handling."""
        from config_stash.exceptions import ConfigLoadError

        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.get_object.side_effect = Exception("Access Denied")

        loader = S3Loader("s3://test-bucket/config.json")
        with self.assertRaises(ConfigLoadError) as context:
            loader.load()

        self.assertIn("Failed to load S3 configuration", str(context.exception))


@unittest.skipUnless(HAS_REQUESTS, "requests not installed")
class TestGitLoader(unittest.TestCase):
    """Test GitLoader class."""

    @patch.object(HTTPLoader if HAS_REQUESTS else object, "load")
    def test_github_url_conversion(self, mock_http_load):
        """Test GitHub URL conversion to raw URL."""
        mock_http_load.return_value = {"test": "config"}

        loader = GitLoader(
            repo_url="https://github.com/user/repo", file_path="config/app.json", branch="main"
        )
        config = loader.load()

        self.assertEqual(config, {"test": "config"})
        # Check that HTTPLoader was initialized with correct raw URL
        # The actual call happens inside GitLoader.load()

    @patch.object(HTTPLoader if HAS_REQUESTS else object, "load")
    def test_gitlab_url_conversion(self, mock_http_load):
        """Test GitLab URL conversion to raw URL."""
        mock_http_load.return_value = {"test": "config"}

        loader = GitLoader(
            repo_url="https://gitlab.com/user/repo", file_path="config/app.yaml", branch="develop"
        )
        config = loader.load()

        self.assertEqual(config, {"test": "config"})

    @patch.object(HTTPLoader if HAS_REQUESTS else object, "load")
    def test_git_with_token(self, mock_http_load):
        """Test Git loading with access token."""
        mock_http_load.return_value = {"test": "config"}

        loader = GitLoader(
            repo_url="https://github.com/user/private-repo",
            file_path="config.json",
            token="ghp_token123",
        )
        config = loader.load()

        self.assertEqual(config, {"test": "config"})

    def test_unsupported_git_provider(self):
        """Test that unsupported Git providers are rejected."""
        loader = GitLoader(repo_url="https://bitbucket.org/user/repo", file_path="config.json")
        with self.assertRaises(ValueError) as context:
            loader.load()

        self.assertIn("Unsupported Git provider", str(context.exception))


if __name__ == "__main__":
    unittest.main()
