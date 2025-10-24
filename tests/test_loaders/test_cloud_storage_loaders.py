"""Tests for cloud storage configuration loaders."""

import os
from unittest.mock import patch

import pytest

from config_stash.loaders.remote_loader import (
    AzureBlobLoader,
    GCPStorageLoader,
    IBMCloudObjectStorageLoader,
    S3Loader,
)


class TestAzureBlobLoader:
    """Test Azure Blob Storage loader."""

    def test_init_with_account_credentials(self):
        """Test initialization with account credentials."""
        loader = AzureBlobLoader(
            container_url="mycontainer",
            blob_name="config.json",
            account_name="myaccount",
            account_key="mykey",
        )
        assert loader.container_url == "mycontainer"
        assert loader.blob_name == "config.json"
        assert loader.account_name == "myaccount"
        assert loader.account_key == "mykey"
        assert loader.url == "azure://mycontainer/config.json"

    def test_init_with_connection_string(self):
        """Test initialization with connection string."""
        loader = AzureBlobLoader(
            container_url="mycontainer",
            blob_name="config.json",
            connection_string="DefaultEndpointsProtocol=https;AccountName=myaccount;...",
        )
        assert (
            loader.connection_string == "DefaultEndpointsProtocol=https;AccountName=myaccount;..."
        )

    def test_init_with_sas_token(self):
        """Test initialization with SAS token."""
        loader = AzureBlobLoader(
            container_url="mycontainer",
            blob_name="config.json",
            account_name="myaccount",
            sas_token="?sv=2020-08-04&ss=b&srt=sco&...",
        )
        assert loader.sas_token == "?sv=2020-08-04&ss=b&srt=sco&..."

    @patch("config_stash.loaders.remote_loader.os.environ.get")
    def test_init_with_env_vars(self, mock_env):
        """Test initialization with environment variables."""
        mock_env.side_effect = lambda key, default=None: {
            "AZURE_STORAGE_ACCOUNT": "env_account",
            "AZURE_STORAGE_KEY": "env_key",
        }.get(key, default)

        loader = AzureBlobLoader(container_url="mycontainer", blob_name="config.json")
        assert loader.account_name == "env_account"
        assert loader.account_key == "env_key"

    def test_load_missing_azure_sdk(self):
        """Test loading when azure-storage-blob is not installed."""
        loader = AzureBlobLoader(
            container_url="mycontainer",
            blob_name="config.json",
            account_name="myaccount",
            account_key="mykey",
        )

        with patch.dict("sys.modules", {"azure.storage.blob": None}):
            with pytest.raises(ImportError) as exc_info:
                loader.load()
            assert "azure-storage-blob is required" in str(exc_info.value)


class TestGCPStorageLoader:
    """Test Google Cloud Storage loader."""

    def test_init_with_credentials(self):
        """Test initialization with service account credentials."""
        loader = GCPStorageLoader(
            bucket_name="mybucket",
            blob_name="config.json",
            project_id="myproject",
            credentials_path="/path/to/creds.json",
        )
        assert loader.bucket_name == "mybucket"
        assert loader.blob_name == "config.json"
        assert loader.project_id == "myproject"
        assert loader.credentials_path == "/path/to/creds.json"
        assert loader.url == "gs://mybucket/config.json"

    @patch("config_stash.loaders.remote_loader.os.environ.get")
    def test_init_with_env_vars(self, mock_env):
        """Test initialization with environment variables."""
        mock_env.side_effect = lambda key, default=None: {
            "GCP_PROJECT_ID": "env_project",
            "GOOGLE_APPLICATION_CREDENTIALS": "/env/path/creds.json",
        }.get(key, default)

        loader = GCPStorageLoader(bucket_name="mybucket", blob_name="config.json")
        assert loader.project_id == "env_project"
        assert loader.credentials_path == "/env/path/creds.json"

    def test_load_missing_gcp_sdk(self):
        """Test loading when google-cloud-storage is not installed."""
        loader = GCPStorageLoader(bucket_name="mybucket", blob_name="config.json")

        with patch.dict("sys.modules", {"google.cloud": None}):
            with pytest.raises(ImportError) as exc_info:
                loader.load()
            assert "google-cloud-storage is required" in str(exc_info.value)


class TestIBMCloudObjectStorageLoader:
    """Test IBM Cloud Object Storage loader."""

    def test_init_with_credentials(self):
        """Test initialization with API credentials."""
        loader = IBMCloudObjectStorageLoader(
            bucket_name="mybucket",
            object_key="configs/app.json",
            api_key="my_api_key",
            service_instance_id="my_instance_id",
            region="us-south",
        )
        assert loader.bucket_name == "mybucket"
        assert loader.object_key == "configs/app.json"
        assert loader.api_key == "my_api_key"
        assert loader.service_instance_id == "my_instance_id"
        assert loader.region == "us-south"
        assert loader.url == "ibmcos://mybucket/configs/app.json"

    def test_init_with_custom_endpoint(self):
        """Test initialization with custom endpoint."""
        loader = IBMCloudObjectStorageLoader(
            bucket_name="mybucket",
            object_key="config.json",
            endpoint_url="https://custom.endpoint.com",
        )
        assert loader.endpoint_url == "https://custom.endpoint.com"

    def test_init_default_endpoint(self):
        """Test initialization with default endpoint based on region."""
        loader = IBMCloudObjectStorageLoader(
            bucket_name="mybucket",
            object_key="config.json",
            region="eu-gb",
        )
        assert loader.endpoint_url == "https://s3.eu-gb.cloud-object-storage.appdomain.cloud"

    @patch("config_stash.loaders.remote_loader.os.environ.get")
    def test_init_with_env_vars(self, mock_env):
        """Test initialization with environment variables."""
        mock_env.side_effect = lambda key, default=None: {
            "IBM_API_KEY": "env_api_key",
            "IBM_SERVICE_INSTANCE_ID": "env_instance_id",
        }.get(key, default)

        loader = IBMCloudObjectStorageLoader(bucket_name="mybucket", object_key="config.json")
        assert loader.api_key == "env_api_key"
        assert loader.service_instance_id == "env_instance_id"

    def test_load_missing_ibm_sdk(self):
        """Test loading when ibm-cos-sdk is not installed."""
        loader = IBMCloudObjectStorageLoader(bucket_name="mybucket", object_key="config.json")

        with patch.dict("sys.modules", {"ibm_boto3": None}):
            with pytest.raises(ImportError) as exc_info:
                loader.load()
            assert "ibm-cos-sdk is required" in str(exc_info.value)


class TestCloudLoaderIntegration:
    """Integration tests for cloud loaders."""

    def test_all_loaders_inherit_from_remote_loader(self):
        """Test that all cloud loaders inherit from RemoteLoader."""
        from config_stash.loaders.remote_loader import RemoteLoader

        assert issubclass(S3Loader, RemoteLoader)
        assert issubclass(AzureBlobLoader, RemoteLoader)
        assert issubclass(GCPStorageLoader, RemoteLoader)
        assert issubclass(IBMCloudObjectStorageLoader, RemoteLoader)

    def test_all_loaders_have_load_method(self):
        """Test that all cloud loaders have load method."""
        loaders = [
            S3Loader("s3://bucket/key"),
            AzureBlobLoader("container", "blob"),
            GCPStorageLoader("bucket", "blob"),
            IBMCloudObjectStorageLoader("bucket", "key"),
        ]

        for loader in loaders:
            assert hasattr(loader, "load")
            assert callable(loader.load)

    def test_all_loaders_set_url(self):
        """Test that all cloud loaders set proper URL."""
        s3_loader = S3Loader("s3://mybucket/mykey")
        assert s3_loader.url == "s3://mybucket/mykey"

        azure_loader = AzureBlobLoader("mycontainer", "myblob")
        assert azure_loader.url == "azure://mycontainer/myblob"

        gcp_loader = GCPStorageLoader("mybucket", "myblob")
        assert gcp_loader.url == "gs://mybucket/myblob"

        ibm_loader = IBMCloudObjectStorageLoader("mybucket", "mykey")
        assert ibm_loader.url == "ibmcos://mybucket/mykey"

    def test_all_loaders_have_config_attribute(self):
        """Test that all cloud loaders have config attribute."""
        loaders = [
            S3Loader("s3://bucket/key"),
            AzureBlobLoader("container", "blob"),
            GCPStorageLoader("bucket", "blob"),
            IBMCloudObjectStorageLoader("bucket", "key"),
        ]

        for loader in loaders:
            assert hasattr(loader, "config")
            assert loader.config == {}

    def test_container_url_parsing(self):
        """Test Azure container URL parsing."""
        # Test with simple container name
        loader = AzureBlobLoader("mycontainer", "blob.json")
        assert loader.container_url == "mycontainer"

        # Test with URL-like container
        loader = AzureBlobLoader("https://account.blob.core.windows.net/mycontainer", "blob.json")
        assert loader.container_url == "https://account.blob.core.windows.net/mycontainer"
