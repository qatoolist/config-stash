"""Remote configuration loaders for Config-Stash."""

import logging
import os
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

from config_stash.exceptions import ConfigLoadError

logger = logging.getLogger(__name__)

# requests is optional
HAS_REQUESTS: bool = False
try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    logger.warning("requests not installed. Remote loading disabled.")


class RemoteLoader:
    """Base class for remote configuration loading.

    RemoteLoader provides the shared interface and common attributes for
    all remote configuration loaders. Subclasses implement the ``load()``
    method to fetch configuration from specific remote backends (HTTP, S3,
    Azure Blob Storage, GCP Storage, Git repositories, IBM COS).

    The loaded content is automatically parsed into a Python dictionary
    based on the file extension or content-type header using the
    ``format_parser`` utility.

    Attributes:
        url: The remote URL or URI identifying the configuration source.
        timeout: Request timeout in seconds.
        headers: HTTP headers sent with the request (where applicable).
        source: Alias for ``url``, used for source tracking.
        config: The loaded configuration dictionary (populated after ``load()``).

    Example:
        >>> # RemoteLoader is abstract; use a concrete subclass:
        >>> loader = HTTPLoader("https://example.com/config.json")
        >>> config_dict = loader.load()
    """

    def __init__(self, url: str, timeout: int = 30, headers: Optional[Dict[str, str]] = None):
        """Initialize remote loader.

        Args:
            url: URL or URI to load configuration from.
            timeout: Request timeout in seconds. Defaults to 30.
            headers: Optional HTTP headers to include in requests.
        """
        self.url = url
        self.timeout = timeout
        self.headers = headers or {}
        self.source = url
        self.config: Dict[str, Any] = {}

    def load(self) -> Dict[str, Any]:
        """Load configuration from remote source.

        Returns:
            Dictionary containing the loaded configuration.

        Raises:
            NotImplementedError: Always; subclasses must override this method.
        """
        raise NotImplementedError


class HTTPLoader(RemoteLoader):
    """Load configuration from HTTP/HTTPS endpoints.

    HTTPLoader fetches configuration files from any HTTP or HTTPS URL. The
    response content-type header is used to determine the configuration
    format; if the content-type is ambiguous, the URL's file extension is
    used as a fallback. Supports JSON, YAML, and TOML formats.

    Attributes:
        url: The HTTP/HTTPS URL of the configuration resource.
        timeout: Request timeout in seconds.
        headers: HTTP headers sent with the request.
        auth: Optional basic-auth credentials as a ``(username, password)`` tuple.
        config: The loaded configuration dictionary.

    Example:
        >>> from config_stash.loaders.remote_loader import HTTPLoader
        >>> loader = HTTPLoader(
        ...     "https://config-server.example.com/app/config.yaml",
        ...     headers={"X-API-Key": "secret"},
        ...     timeout=10,
        ... )
        >>> config_dict = loader.load()
        >>> print(config_dict["database"]["host"])

    Note:
        Requires the ``requests`` package. Install it with::

            pip install requests
    """

    def __init__(
        self,
        url: str,
        timeout: int = 30,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[Tuple[str, str]] = None,
    ):
        """Initialize HTTP loader.

        Args:
            url: HTTP/HTTPS URL to fetch configuration from.
            timeout: Request timeout in seconds. Defaults to 30.
            headers: Optional HTTP headers (e.g., API keys).
            auth: Optional ``(username, password)`` tuple for HTTP Basic Auth.

        Raises:
            ImportError: If the ``requests`` package is not installed.
        """
        if not HAS_REQUESTS:
            raise ImportError(
                "requests is required for HTTP loading. Install with: pip install requests"
            )

        super().__init__(url, timeout, headers)
        self.auth = auth

    def load(self) -> Dict[str, Any]:
        """Load configuration from an HTTP/HTTPS endpoint.

        Sends a GET request to the configured URL, detects the response
        format from the content-type header or URL extension, and parses
        the content into a dictionary.

        Returns:
            Dictionary containing the loaded configuration.

        Raises:
            ConfigLoadError: If the HTTP request fails or the response
                content cannot be parsed.

        Example:
            >>> loader = HTTPLoader("https://example.com/config.json")
            >>> config = loader.load()
        """
        try:
            logger.info(f"Loading configuration from {self.url}")
            response = requests.get(
                self.url, timeout=self.timeout, headers=self.headers, auth=self.auth
            )
            response.raise_for_status()

            # Detect format from content-type or URL
            from config_stash.utils.format_parser import parse_config_content

            content_type = response.headers.get("content-type", "")

            # Map content-type to a pseudo-filename for format detection
            if "yaml" in content_type:
                format_hint = "response.yaml"
            elif "toml" in content_type:
                format_hint = "response.toml"
            elif "json" in content_type:
                format_hint = "response.json"
            else:
                format_hint = self.url  # Use URL extension

            self.config = parse_config_content(response.text, format_hint)

            logger.info(f"Successfully loaded configuration from {self.url}")
            return self.config

        except requests.RequestException as e:
            logger.error(f"Failed to load configuration from {self.url}: {e}")
            raise ConfigLoadError(
                f"Failed to load remote configuration from {self.url}",
                source=self.url,
                loader_type=self.__class__.__name__,
                original_error=e,
            ) from e
        except Exception as e:
            logger.error(f"Failed to parse configuration from {self.url}: {e}")
            raise ConfigLoadError(
                f"Failed to parse remote configuration from {self.url}",
                source=self.url,
                loader_type=self.__class__.__name__,
                original_error=e,
            ) from e


class S3Loader(RemoteLoader):
    """Load configuration from AWS S3.

    S3Loader fetches configuration files stored in Amazon S3 buckets.
    Authentication can be provided explicitly via access keys, or
    implicitly through IAM roles, environment variables
    (``AWS_ACCESS_KEY_ID``, ``AWS_SECRET_ACCESS_KEY``), or the default
    boto3 credential chain.

    Attributes:
        url: The original ``s3://`` URL.
        bucket: The S3 bucket name (parsed from the URL).
        key: The object key / path within the bucket.
        aws_access_key: AWS access key ID (may be None for IAM).
        aws_secret_key: AWS secret access key (may be None for IAM).
        region: AWS region name.
        config: The loaded configuration dictionary.

    Example:
        >>> from config_stash.loaders.remote_loader import S3Loader
        >>> loader = S3Loader("s3://my-bucket/configs/app.yaml", region="eu-west-1")
        >>> config_dict = loader.load()

    Note:
        Requires the ``boto3`` package. Install it with::

            pip install boto3
    """

    def __init__(
        self,
        s3_url: str,
        aws_access_key: Optional[str] = None,
        aws_secret_key: Optional[str] = None,
        region: str = "us-east-1",
    ):
        """Initialize S3 loader.

        Args:
            s3_url: S3 URL in the form ``s3://bucket/path/to/config.json``.
            aws_access_key: AWS access key ID. Falls back to the
                ``AWS_ACCESS_KEY_ID`` environment variable or IAM role.
            aws_secret_key: AWS secret access key. Falls back to the
                ``AWS_SECRET_ACCESS_KEY`` environment variable or IAM role.
            region: AWS region name. Defaults to ``"us-east-1"``.

        Raises:
            ValueError: If the URL scheme is not ``s3``.
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
        """Load configuration from an AWS S3 bucket.

        Downloads the object specified by ``bucket`` and ``key``, then
        parses the content based on the file extension of the key.

        Returns:
            Dictionary containing the loaded configuration.

        Raises:
            ImportError: If ``boto3`` is not installed.
            ConfigLoadError: If the S3 request fails or the content
                cannot be parsed.

        Example:
            >>> loader = S3Loader("s3://my-bucket/config.yaml")
            >>> config = loader.load()
        """
        try:
            import boto3  # type: ignore[import-untyped]
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
            from config_stash.utils.format_parser import parse_config_content

            self.config = parse_config_content(content, self.key)

            logger.info(f"Successfully loaded configuration from S3: {self.url}")
            return self.config

        except ConfigLoadError:
            # Re-raise ConfigLoadError as-is
            raise
        except Exception as e:
            logger.error(f"Failed to load configuration from S3: {e}")
            raise ConfigLoadError(
                f"Failed to load S3 configuration from {self.url}",
                source=self.url,
                loader_type=self.__class__.__name__,
                original_error=e,
            ) from e


class GitLoader(RemoteLoader):
    """Load configuration from a Git repository hosted on GitHub or GitLab.

    GitLoader constructs a raw-content URL for the specified file and branch,
    then delegates to HTTPLoader to fetch and parse it. Private repositories
    are supported via personal access tokens.

    Attributes:
        url: The Git repository URL (e.g., ``https://github.com/org/repo``).
        file_path: Path to the configuration file within the repository.
        branch: The Git branch to read from.
        token: Access token for private repositories (may be None).
        config: The loaded configuration dictionary.

    Example:
        >>> from config_stash.loaders.remote_loader import GitLoader
        >>> loader = GitLoader(
        ...     repo_url="https://github.com/myorg/myrepo",
        ...     file_path="config/production.yaml",
        ...     branch="main",
        ...     token="ghp_xxxxxxxxxxxx",
        ... )
        >>> config_dict = loader.load()

    Note:
        Currently supports GitHub and GitLab. The ``GIT_TOKEN`` environment
        variable is used as a fallback when ``token`` is not provided.
    """

    def __init__(
        self, repo_url: str, file_path: str, branch: str = "main", token: Optional[str] = None
    ):
        """Initialize Git loader.

        Args:
            repo_url: Git repository URL (GitHub or GitLab).
            file_path: Path to the configuration file within the repository.
            branch: Git branch to read from. Defaults to ``"main"``.
            token: Access token for private repositories. Falls back to
                the ``GIT_TOKEN`` environment variable.
        """
        super().__init__(repo_url)
        self.file_path = file_path
        self.branch = branch
        self.token = token or os.environ.get("GIT_TOKEN")

    def load(self) -> Dict[str, Any]:
        """Load configuration from a Git repository.

        Converts the repository URL to a raw-content URL based on the
        hosting provider (GitHub or GitLab), then fetches the file via
        HTTPLoader.

        Returns:
            Dictionary containing the loaded configuration.

        Raises:
            ValueError: If the Git provider is not supported (neither
                GitHub nor GitLab).
            ConfigLoadError: If the HTTP request or parsing fails.

        Example:
            >>> loader = GitLoader(
            ...     "https://github.com/org/repo", "config.yaml"
            ... )
            >>> config = loader.load()
        """
        # Convert to raw URL based on provider
        if "github.com" in self.url:
            # GitHub raw URL format
            parts = self.url.replace("https://github.com/", "").split("/")
            repo = parts[1].removesuffix(".git") if len(parts) > 1 else parts[0]
            raw_url = f"https://raw.githubusercontent.com/{parts[0]}/{repo}/{self.branch}/{self.file_path}"
        elif "gitlab.com" in self.url:
            # GitLab raw URL format — handle subgroups by joining all path parts
            path = self.url.replace("https://gitlab.com/", "").removesuffix(".git")
            raw_url = (
                f"https://gitlab.com/{path}/-/raw/{self.branch}/{self.file_path}"
            )
        else:
            raise ValueError(f"Unsupported Git provider: {self.url}")

        # Use HTTP loader to fetch the raw file
        headers = {}
        if self.token:
            if "gitlab.com" in self.url:
                headers["PRIVATE-TOKEN"] = self.token
            else:
                headers["Authorization"] = f"token {self.token}"

        http_loader = HTTPLoader(raw_url, headers=headers)
        self.config = http_loader.load()
        return self.config


class AzureBlobLoader(RemoteLoader):
    """Load configuration from Azure Blob Storage.

    AzureBlobLoader downloads configuration files from Azure Blob Storage
    containers. It supports multiple authentication methods: connection
    strings, account key, SAS tokens, and Azure Managed Identity via
    ``DefaultAzureCredential``.

    Attributes:
        url: Synthetic URI in the form ``azure://<container>/<blob>``.
        container_url: The Azure container URL or container name.
        blob_name: The blob (file) name within the container.
        account_name: Azure Storage account name.
        account_key: Azure Storage account key (may be None).
        sas_token: Shared Access Signature token (may be None).
        connection_string: Full Azure Storage connection string (may be None).
        config: The loaded configuration dictionary.

    Example:
        >>> from config_stash.loaders.remote_loader import AzureBlobLoader
        >>> loader = AzureBlobLoader(
        ...     container_url="my-container",
        ...     blob_name="config/app.yaml",
        ...     account_name="mystorageaccount",
        ...     account_key="base64key==",
        ... )
        >>> config_dict = loader.load()

    Note:
        Requires the ``azure-storage-blob`` package. Install it with::

            pip install azure-storage-blob

        Environment variable fallbacks: ``AZURE_STORAGE_ACCOUNT``,
        ``AZURE_STORAGE_KEY``, ``AZURE_SAS_TOKEN``,
        ``AZURE_STORAGE_CONNECTION_STRING``.
    """

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
            container_url: Azure container URL or plain container name.
            blob_name: Name of the blob (file) to load.
            account_name: Azure storage account name. Falls back to
                ``AZURE_STORAGE_ACCOUNT`` environment variable.
            account_key: Azure storage account key. Falls back to
                ``AZURE_STORAGE_KEY`` environment variable.
            sas_token: Shared Access Signature token. Falls back to
                ``AZURE_SAS_TOKEN`` environment variable.
            connection_string: Full connection string (alternative to
                individual credentials). Falls back to
                ``AZURE_STORAGE_CONNECTION_STRING`` environment variable.
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
        """Load configuration from Azure Blob Storage.

        Downloads the blob content and parses it based on the blob
        name's file extension (e.g., ``.yaml``, ``.json``, ``.toml``).

        Returns:
            Dictionary containing the loaded configuration.

        Raises:
            ImportError: If ``azure-storage-blob`` is not installed.
            ValueError: If ``account_name`` is required but not provided.
            ConfigLoadError: If the Azure request fails or the content
                cannot be parsed.

        Example:
            >>> loader = AzureBlobLoader("my-container", "config.yaml",
            ...                          account_name="myaccount")
            >>> config = loader.load()
        """
        try:
            from azure.storage.blob import BlobServiceClient  # type: ignore[import-untyped]
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
                if not self.account_name:
                    raise ValueError(
                        "Azure storage account name is required. Provide 'account_name' "
                        "or set the AZURE_STORAGE_ACCOUNT environment variable."
                    )
                from azure.identity import DefaultAzureCredential  # type: ignore[import-untyped]

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
            from config_stash.utils.format_parser import parse_config_content

            self.config = parse_config_content(content, self.blob_name)

            logger.info(f"Successfully loaded configuration from Azure: {self.url}")
            return self.config

        except ConfigLoadError:
            # Re-raise ConfigLoadError as-is
            raise
        except Exception as e:
            logger.error(f"Failed to load configuration from Azure: {e}")
            raise ConfigLoadError(
                f"Failed to load Azure configuration from {self.url}",
                source=self.url,
                loader_type=self.__class__.__name__,
                original_error=e,
            ) from e


class GCPStorageLoader(RemoteLoader):
    """Load configuration from Google Cloud Storage.

    GCPStorageLoader downloads configuration files from GCS buckets.
    Authentication is handled via explicit service account credentials
    or Application Default Credentials (ADC).

    Attributes:
        url: Synthetic URI in the form ``gs://<bucket>/<blob>``.
        bucket_name: The GCS bucket name.
        blob_name: The blob (file) name within the bucket.
        project_id: GCP project ID.
        credentials_path: Path to a service account JSON key file.
        config: The loaded configuration dictionary.

    Example:
        >>> from config_stash.loaders.remote_loader import GCPStorageLoader
        >>> loader = GCPStorageLoader(
        ...     bucket_name="my-config-bucket",
        ...     blob_name="services/app.yaml",
        ...     project_id="my-gcp-project",
        ... )
        >>> config_dict = loader.load()

    Note:
        Requires the ``google-cloud-storage`` package. Install it with::

            pip install google-cloud-storage

        Environment variable fallbacks: ``GCP_PROJECT_ID``,
        ``GOOGLE_APPLICATION_CREDENTIALS``.
    """

    def __init__(
        self,
        bucket_name: str,
        blob_name: str,
        project_id: Optional[str] = None,
        credentials_path: Optional[str] = None,
    ):
        """Initialize GCP Storage loader.

        Args:
            bucket_name: GCS bucket name.
            blob_name: Name of the blob (file) to load.
            project_id: GCP project ID. Falls back to the
                ``GCP_PROJECT_ID`` environment variable.
            credentials_path: Path to a service account JSON key file.
                Falls back to the ``GOOGLE_APPLICATION_CREDENTIALS``
                environment variable.
        """
        super().__init__(f"gs://{bucket_name}/{blob_name}")
        self.bucket_name = bucket_name
        self.blob_name = blob_name
        self.project_id = project_id or os.environ.get("GCP_PROJECT_ID")
        self.credentials_path = credentials_path or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    def load(self) -> Dict[str, Any]:
        """Load configuration from Google Cloud Storage.

        Downloads the blob content as text and parses it based on the
        blob name's file extension.

        Returns:
            Dictionary containing the loaded configuration.

        Raises:
            ImportError: If ``google-cloud-storage`` is not installed.
            ConfigLoadError: If the GCS request fails or the content
                cannot be parsed.

        Example:
            >>> loader = GCPStorageLoader("my-bucket", "config.yaml")
            >>> config = loader.load()
        """
        try:
            from google.cloud import storage  # type: ignore[import-untyped]
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
            from config_stash.utils.format_parser import parse_config_content

            self.config = parse_config_content(content, self.blob_name)

            logger.info(f"Successfully loaded configuration from GCS: {self.url}")
            return self.config

        except ConfigLoadError:
            # Re-raise ConfigLoadError as-is
            raise
        except Exception as e:
            logger.error(f"Failed to load configuration from GCS: {e}")
            raise ConfigLoadError(
                f"Failed to load GCS configuration from {self.url}",
                source=self.url,
                loader_type=self.__class__.__name__,
                original_error=e,
            ) from e


class IBMCloudObjectStorageLoader(RemoteLoader):
    """Load configuration from IBM Cloud Object Storage.

    IBMCloudObjectStorageLoader fetches configuration files stored in IBM
    Cloud Object Storage (COS) buckets using the S3-compatible API provided
    by the ``ibm-cos-sdk`` package. Authentication uses IBM IAM OAuth via
    an API key and service instance ID.

    Attributes:
        url: Synthetic URI in the form ``ibmcos://<bucket>/<key>``.
        bucket_name: The IBM COS bucket name.
        object_key: The object key (path) within the bucket.
        api_key: IBM Cloud API key.
        service_instance_id: IBM COS service instance ID.
        region: IBM Cloud region (e.g., ``"us-south"``).
        endpoint_url: The S3-compatible endpoint URL.
        config: The loaded configuration dictionary.

    Example:
        >>> from config_stash.loaders.remote_loader import IBMCloudObjectStorageLoader
        >>> loader = IBMCloudObjectStorageLoader(
        ...     bucket_name="my-config-bucket",
        ...     object_key="app/config.yaml",
        ...     api_key="ibm-api-key",
        ...     service_instance_id="crn:v1:...",
        ... )
        >>> config_dict = loader.load()

    Note:
        Requires the ``ibm-cos-sdk`` package. Install it with::

            pip install ibm-cos-sdk

        Environment variable fallbacks: ``IBM_API_KEY``,
        ``IBM_SERVICE_INSTANCE_ID``.
    """

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
            bucket_name: IBM COS bucket name.
            object_key: Key (path) of the object to load.
            api_key: IBM Cloud API key. Falls back to the
                ``IBM_API_KEY`` environment variable.
            service_instance_id: IBM COS service instance ID. Falls back
                to the ``IBM_SERVICE_INSTANCE_ID`` environment variable.
            endpoint_url: Custom S3-compatible endpoint URL. Defaults to
                the public endpoint for the given region.
            region: IBM Cloud region. Defaults to ``"us-south"``.
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
        """Load configuration from IBM Cloud Object Storage.

        Downloads the object content and parses it based on the object
        key's file extension.

        Returns:
            Dictionary containing the loaded configuration.

        Raises:
            ImportError: If ``ibm-cos-sdk`` is not installed.
            ConfigLoadError: If the IBM COS request fails or the content
                cannot be parsed.

        Example:
            >>> loader = IBMCloudObjectStorageLoader(
            ...     "my-bucket", "config.yaml"
            ... )
            >>> config = loader.load()
        """
        try:
            import ibm_boto3  # type: ignore[import-untyped]
            from ibm_botocore.client import Config as IBMConfig  # type: ignore[import-untyped]
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
                config=IBMConfig(signature_version="oauth"),
                endpoint_url=self.endpoint_url,
            )

            # Get object from IBM COS
            response = cos_client.get_object(Bucket=self.bucket_name, Key=self.object_key)
            content = response["Body"].read().decode("utf-8")

            # Parse based on file extension
            from config_stash.utils.format_parser import parse_config_content

            self.config = parse_config_content(content, self.object_key)

            logger.info(f"Successfully loaded configuration from IBM COS: {self.url}")
            return self.config

        except ConfigLoadError:
            # Re-raise ConfigLoadError as-is
            raise
        except Exception as e:
            logger.error(f"Failed to load configuration from IBM COS: {e}")
            raise ConfigLoadError(
                f"Failed to load IBM COS configuration from {self.url}",
                source=self.url,
                loader_type=self.__class__.__name__,
                original_error=e,
            ) from e
