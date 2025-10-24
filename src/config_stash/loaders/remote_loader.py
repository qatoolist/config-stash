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
        self.config: Dict[str, Any] = {}

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


class AzureBlobLoader(RemoteLoader):
    """Load configuration from Azure Blob Storage."""

    def __init__(
        self,
        container_url: str,
        blob_name: str,
        account_name: Optional[str] = None,
        account_key: Optional[str] = None,
        sas_token: Optional[str] = None,
        connection_string: Optional[str] = None,
    ):
        """Initialize Azure Blob loader.

        Args:
            container_url: Azure container URL or container name
            blob_name: Name of the blob (file) to load
            account_name: Azure storage account name
            account_key: Azure storage account key
            sas_token: Shared Access Signature token for authentication
            connection_string: Full connection string (alternative to account credentials)
        """
        super().__init__(f"azure://{container_url}/{blob_name}")
        self.container_url = container_url
        self.blob_name = blob_name
        self.account_name = account_name or os.environ.get("AZURE_STORAGE_ACCOUNT")
        self.account_key = account_key or os.environ.get("AZURE_STORAGE_KEY")
        self.sas_token = sas_token or os.environ.get("AZURE_SAS_TOKEN")
        self.connection_string = connection_string or os.environ.get(
            "AZURE_STORAGE_CONNECTION_STRING"
        )

    def load(self) -> Dict[str, Any]:
        """Load configuration from Azure Blob Storage."""
        try:
            from azure.storage.blob import BlobServiceClient
        except ImportError:
            raise ImportError(
                "azure-storage-blob is required for Azure loading. "
                "Install with: pip install azure-storage-blob"
            )

        try:
            logger.info(f"Loading configuration from Azure: {self.url}")

            # Create blob client based on available credentials
            if self.connection_string:
                blob_service = BlobServiceClient.from_connection_string(self.connection_string)
            elif self.account_name and self.account_key:
                blob_service = BlobServiceClient(
                    account_url=f"https://{self.account_name}.blob.core.windows.net",
                    credential=self.account_key,
                )
            elif self.account_name and self.sas_token:
                blob_service = BlobServiceClient(
                    account_url=f"https://{self.account_name}.blob.core.windows.net",
                    credential=self.sas_token,
                )
            else:
                # Try DefaultAzureCredential for managed identity
                from azure.identity import DefaultAzureCredential

                blob_service = BlobServiceClient(
                    account_url=f"https://{self.account_name}.blob.core.windows.net",
                    credential=DefaultAzureCredential(),
                )

            # Extract container name if full URL provided
            container_name = (
                self.container_url.split("/")[-1]
                if "/" in self.container_url
                else self.container_url
            )

            # Get blob client and download content
            blob_client = blob_service.get_blob_client(
                container=container_name, blob=self.blob_name
            )
            content = blob_client.download_blob().readall().decode("utf-8")

            # Parse based on file extension
            if self.blob_name.endswith(".json"):
                self.config = json.loads(content)
            elif self.blob_name.endswith((".yaml", ".yml")):
                import yaml

                self.config = yaml.safe_load(content)
            elif self.blob_name.endswith(".toml"):
                import toml

                self.config = toml.loads(content)
            else:
                # Try JSON as default
                self.config = json.loads(content)

            logger.info(f"Successfully loaded configuration from Azure: {self.url}")
            return self.config

        except Exception as e:
            logger.error(f"Failed to load configuration from Azure: {e}")
            raise RuntimeError(f"Failed to load Azure configuration: {e}")


class GCPStorageLoader(RemoteLoader):
    """Load configuration from Google Cloud Storage."""

    def __init__(
        self,
        bucket_name: str,
        blob_name: str,
        project_id: Optional[str] = None,
        credentials_path: Optional[str] = None,
    ):
        """Initialize GCP Storage loader.

        Args:
            bucket_name: GCS bucket name
            blob_name: Name of the blob (file) to load
            project_id: GCP project ID
            credentials_path: Path to service account JSON file
        """
        super().__init__(f"gs://{bucket_name}/{blob_name}")
        self.bucket_name = bucket_name
        self.blob_name = blob_name
        self.project_id = project_id or os.environ.get("GCP_PROJECT_ID")
        self.credentials_path = credentials_path or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    def load(self) -> Dict[str, Any]:
        """Load configuration from Google Cloud Storage."""
        try:
            from google.cloud import storage
        except ImportError:
            raise ImportError(
                "google-cloud-storage is required for GCS loading. "
                "Install with: pip install google-cloud-storage"
            )

        try:
            logger.info(f"Loading configuration from GCS: {self.url}")

            # Create storage client
            if self.credentials_path:
                # Use service account credentials
                from google.oauth2 import service_account

                credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_path
                )
                client = storage.Client(project=self.project_id, credentials=credentials)
            else:
                # Use default credentials (ADC)
                client = storage.Client(project=self.project_id)

            # Get bucket and blob
            bucket = client.bucket(self.bucket_name)
            blob = bucket.blob(self.blob_name)

            # Download content
            content = blob.download_as_text()

            # Parse based on file extension
            if self.blob_name.endswith(".json"):
                self.config = json.loads(content)
            elif self.blob_name.endswith((".yaml", ".yml")):
                import yaml

                self.config = yaml.safe_load(content)
            elif self.blob_name.endswith(".toml"):
                import toml

                self.config = toml.loads(content)
            else:
                # Try JSON as default
                self.config = json.loads(content)

            logger.info(f"Successfully loaded configuration from GCS: {self.url}")
            return self.config

        except Exception as e:
            logger.error(f"Failed to load configuration from GCS: {e}")
            raise RuntimeError(f"Failed to load GCS configuration: {e}")


class IBMCloudObjectStorageLoader(RemoteLoader):
    """Load configuration from IBM Cloud Object Storage."""

    def __init__(
        self,
        bucket_name: str,
        object_key: str,
        api_key: Optional[str] = None,
        service_instance_id: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        region: str = "us-south",
    ):
        """Initialize IBM Cloud Object Storage loader.

        Args:
            bucket_name: IBM COS bucket name
            object_key: Key (path) of the object to load
            api_key: IBM Cloud API key
            service_instance_id: IBM COS service instance ID
            endpoint_url: Custom endpoint URL (defaults to public endpoint)
            region: IBM Cloud region (default: us-south)
        """
        super().__init__(f"ibmcos://{bucket_name}/{object_key}")
        self.bucket_name = bucket_name
        self.object_key = object_key
        self.api_key = api_key or os.environ.get("IBM_API_KEY")
        self.service_instance_id = service_instance_id or os.environ.get("IBM_SERVICE_INSTANCE_ID")
        self.region = region
        self.endpoint_url = (
            endpoint_url or f"https://s3.{region}.cloud-object-storage.appdomain.cloud"
        )

    def load(self) -> Dict[str, Any]:
        """Load configuration from IBM Cloud Object Storage."""
        try:
            import ibm_boto3
            from ibm_botocore.client import Config
        except ImportError:
            raise ImportError(
                "ibm-cos-sdk is required for IBM COS loading. "
                "Install with: pip install ibm-cos-sdk"
            )

        try:
            logger.info(f"Loading configuration from IBM COS: {self.url}")

            # Create COS client
            cos_client = ibm_boto3.client(
                "s3",
                ibm_api_key_id=self.api_key,
                ibm_service_instance_id=self.service_instance_id,
                config=Config(signature_version="oauth"),
                endpoint_url=self.endpoint_url,
            )

            # Get object from IBM COS
            response = cos_client.get_object(Bucket=self.bucket_name, Key=self.object_key)
            content = response["Body"].read().decode("utf-8")

            # Parse based on file extension
            if self.object_key.endswith(".json"):
                self.config = json.loads(content)
            elif self.object_key.endswith((".yaml", ".yml")):
                import yaml

                self.config = yaml.safe_load(content)
            elif self.object_key.endswith(".toml"):
                import toml

                self.config = toml.loads(content)
            else:
                # Try JSON as default
                self.config = json.loads(content)

            logger.info(f"Successfully loaded configuration from IBM COS: {self.url}")
            return self.config

        except Exception as e:
            logger.error(f"Failed to load configuration from IBM COS: {e}")
            raise RuntimeError(f"Failed to load IBM COS configuration: {e}")
