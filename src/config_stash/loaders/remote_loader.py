"""Remote configuration loaders for Config-Stash."""

import json
import logging
import os
from typing import Any, Dict, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# requests is optional
try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    logger.warning("requests not installed. Remote loading disabled.")


class RemoteLoader:
    """Base class for remote configuration loading."""

    def __init__(self, url: str, timeout: int = 30, headers: Optional[Dict] = None):
        """Initialize remote loader.

        Args:
            url: URL to load configuration from
            timeout: Request timeout in seconds
            headers: Optional HTTP headers
        """
        self.url = url
        self.timeout = timeout
        self.headers = headers or {}
        self.source = url
        self.config = {}

    def load(self) -> Dict[str, Any]:
        """Load configuration from remote source."""
        raise NotImplementedError


class HTTPLoader(RemoteLoader):
    """Load configuration from HTTP/HTTPS endpoints."""

    def __init__(
        self,
        url: str,
        timeout: int = 30,
        headers: Optional[Dict] = None,
        auth: Optional[tuple] = None,
    ):
        """Initialize HTTP loader.

        Args:
            url: HTTP/HTTPS URL
            timeout: Request timeout
            headers: Optional headers
            auth: Optional (username, password) tuple for basic auth
        """
        if not HAS_REQUESTS:
            raise ImportError(
                "requests is required for HTTP loading. Install with: pip install requests"
            )

        super().__init__(url, timeout, headers)
        self.auth = auth

    def load(self) -> Dict[str, Any]:
        """Load configuration from HTTP endpoint."""
        try:
            logger.info(f"Loading configuration from {self.url}")
            response = requests.get(
                self.url, timeout=self.timeout, headers=self.headers, auth=self.auth
            )
            response.raise_for_status()

            # Detect format from content-type or URL
            content_type = response.headers.get("content-type", "")

            if "json" in content_type or self.url.endswith(".json"):
                self.config = response.json()
            elif "yaml" in content_type or self.url.endswith((".yaml", ".yml")):
                import yaml

                self.config = yaml.safe_load(response.text)
            elif "toml" in content_type or self.url.endswith(".toml"):
                import toml

                self.config = toml.loads(response.text)
            else:
                # Try JSON as default
                self.config = response.json()

            logger.info(f"Successfully loaded configuration from {self.url}")
            return self.config

        except requests.RequestException as e:
            logger.error(f"Failed to load configuration from {self.url}: {e}")
            raise RuntimeError(f"Failed to load remote configuration: {e}")


class S3Loader(RemoteLoader):
    """Load configuration from AWS S3."""

    def __init__(
        self,
        s3_url: str,
        aws_access_key: Optional[str] = None,
        aws_secret_key: Optional[str] = None,
        region: str = "us-east-1",
    ):
        """Initialize S3 loader.

        Args:
            s3_url: S3 URL (s3://bucket/path/to/config.json)
            aws_access_key: AWS access key (or use environment/IAM)
            aws_secret_key: AWS secret key
            region: AWS region
        """
        super().__init__(s3_url)
        self.aws_access_key = aws_access_key or os.environ.get("AWS_ACCESS_KEY_ID")
        self.aws_secret_key = aws_secret_key or os.environ.get("AWS_SECRET_ACCESS_KEY")
        self.region = region

        # Parse S3 URL
        parsed = urlparse(s3_url)
        if parsed.scheme != "s3":
            raise ValueError(f"Invalid S3 URL: {s3_url}")
        self.bucket = parsed.netloc
        self.key = parsed.path.lstrip("/")

    def load(self) -> Dict[str, Any]:
        """Load configuration from S3."""
        try:
            import boto3
        except ImportError:
            raise ImportError("boto3 is required for S3 loading. Install with: pip install boto3")

        try:
            logger.info(f"Loading configuration from S3: {self.url}")

            # Create S3 client
            if self.aws_access_key and self.aws_secret_key:
                s3 = boto3.client(
                    "s3",
                    aws_access_key_id=self.aws_access_key,
                    aws_secret_access_key=self.aws_secret_key,
                    region_name=self.region,
                )
            else:
                # Use default credentials (IAM role, environment, etc.)
                s3 = boto3.client("s3", region_name=self.region)

            # Get object from S3
            response = s3.get_object(Bucket=self.bucket, Key=self.key)
            content = response["Body"].read().decode("utf-8")

            # Parse based on file extension
            if self.key.endswith(".json"):
                self.config = json.loads(content)
            elif self.key.endswith((".yaml", ".yml")):
                import yaml

                self.config = yaml.safe_load(content)
            elif self.key.endswith(".toml"):
                import toml

                self.config = toml.loads(content)
            else:
                # Try JSON as default
                self.config = json.loads(content)

            logger.info(f"Successfully loaded configuration from S3: {self.url}")
            return self.config

        except Exception as e:
            logger.error(f"Failed to load configuration from S3: {e}")
            raise RuntimeError(f"Failed to load S3 configuration: {e}")


class GitLoader(RemoteLoader):
    """Load configuration from Git repository."""

    def __init__(
        self, repo_url: str, file_path: str, branch: str = "main", token: Optional[str] = None
    ):
        """Initialize Git loader.

        Args:
            repo_url: Git repository URL
            file_path: Path to config file in repository
            branch: Git branch
            token: Optional access token for private repos
        """
        super().__init__(repo_url)
        self.file_path = file_path
        self.branch = branch
        self.token = token or os.environ.get("GIT_TOKEN")

    def load(self) -> Dict[str, Any]:
        """Load configuration from Git repository."""
        # Convert to raw URL based on provider
        if "github.com" in self.url:
            # GitHub raw URL format
            parts = self.url.replace("https://github.com/", "").split("/")
            raw_url = f"https://raw.githubusercontent.com/{parts[0]}/{parts[1]}/{self.branch}/{self.file_path}"
        elif "gitlab.com" in self.url:
            # GitLab raw URL format
            parts = self.url.replace("https://gitlab.com/", "").split("/")
            raw_url = (
                f"https://gitlab.com/{parts[0]}/{parts[1]}/-/raw/{self.branch}/{self.file_path}"
            )
        else:
            raise ValueError(f"Unsupported Git provider: {self.url}")

        # Use HTTP loader to fetch the raw file
        headers = {}
        if self.token:
            headers["Authorization"] = f"token {self.token}"

        http_loader = HTTPLoader(raw_url, headers=headers)
        self.config = http_loader.load()
        return self.config
