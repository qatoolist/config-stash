"""Google Cloud Secret Manager secret store provider."""

from typing import Any, Dict, List, Optional

from config_stash.secret_stores.base import (
    SecretAccessError,
    SecretNotFoundError,
    SecretStore,
    SecretStoreError,
)

try:
    from google.api_core import exceptions as gcp_exceptions
    from google.cloud import secretmanager

    GCP_AVAILABLE = True
except ImportError:
    GCP_AVAILABLE = False


class GCPSecretManager(SecretStore):
    """Google Cloud Secret Manager secret store provider.

    This provider integrates with GCP Secret Manager to retrieve secrets.

    Prerequisites:
        pip install google-cloud-secret-manager

    Authentication:
        Uses Application Default Credentials (ADC):
        - GOOGLE_APPLICATION_CREDENTIALS environment variable pointing to service account key
        - gcloud auth application-default login
        - Automatic when running on GCP (Compute Engine, Cloud Run, etc.)

    Example:
        >>> from config_stash import Config
        >>> from config_stash.secret_stores import GCPSecretManager, SecretResolver
        >>>
        >>> # Initialize with project ID
        >>> store = GCPSecretManager(project_id='my-gcp-project')
        >>>
        >>> # Use with Config
        >>> config = Config(secret_resolver=SecretResolver(store))
        >>>
        >>> # In config file: database.password = "${"secret" + ":" + "db-password"}"
        >>> # Resolves to: projects/my-gcp-project/secrets/db-password/versions/latest
    """

    def __init__(self, project_id: str, credentials: Optional[Any] = None) -> None:
        """Initialize GCP Secret Manager client.

        Args:
            project_id: GCP project ID.
            credentials: Optional google.auth.credentials.Credentials object.
                If None, uses Application Default Credentials.

        Raises:
            ImportError: If Google Cloud SDK is not installed.
            SecretAccessError: If authentication fails.

        Example:
            >>> # Use default credentials
            >>> store = GCPSecretManager(project_id='my-project')
            >>>
            >>> # Use specific credentials
            >>> from google.oauth2 import service_account
            >>> creds = service_account.Credentials.from_service_account_file(
            ...     'path/to/key.json'
            ... )
            >>> store = GCPSecretManager(project_id='my-project', credentials=creds)
        """
        if not GCP_AVAILABLE:
            raise ImportError(
                "google-cloud-secret-manager is required for GCPSecretManager. "
                "Install with: pip install google-cloud-secret-manager"
            )

        self.project_id = project_id
        self.project_path = f"projects/{project_id}"

        try:
            if credentials:
                self.client = secretmanager.SecretManagerServiceClient(credentials=credentials)
            else:
                self.client = secretmanager.SecretManagerServiceClient()
        except Exception as e:
            raise SecretAccessError(f"Failed to initialize GCP Secret Manager client: {e}")

    def get_secret(self, key: str, version: Optional[str] = None, **kwargs) -> Any:
        """Retrieve a secret from GCP Secret Manager.

        Args:
            key: The secret name (not the full resource path).
            version: Optional version identifier. Can be:
                - Version number (e.g., "1", "2")
                - "latest" (default if not specified)
            **kwargs: Additional parameters.

        Returns:
            The secret value as bytes or string.

        Raises:
            SecretNotFoundError: If the secret doesn't exist.
            SecretAccessError: If there's a permission error.
            SecretStoreError: For other GCP errors.

        Example:
            >>> store = GCPSecretManager(project_id='my-project')
            >>>
            >>> # Get latest version
            >>> password = store.get_secret("db-password")
            >>>
            >>> # Get specific version
            >>> old_password = store.get_secret("db-password", version="1")
        """
        if version is None:
            version = "latest"

        # Build the resource name
        name = f"{self.project_path}/secrets/{key}/versions/{version}"

        try:
            response = self.client.access_secret_version(request={"name": name})
            payload = response.payload.data

            # Try to decode as UTF-8 string
            try:
                return payload.decode("UTF-8")
            except UnicodeDecodeError:
                # Return raw bytes if not UTF-8
                return payload

        except gcp_exceptions.NotFound:
            raise SecretNotFoundError(
                f"Secret '{key}' (version: {version}) not found in GCP project '{self.project_id}'"
            )
        except gcp_exceptions.PermissionDenied as e:
            raise SecretAccessError(f"Access denied to secret '{key}': {e}")
        except Exception as e:
            raise SecretStoreError(f"GCP Secret Manager error for '{key}': {e}")

    def set_secret(self, key: str, value: Any, **kwargs) -> None:
        """Store a secret in GCP Secret Manager.

        Args:
            key: The secret name.
            value: The secret value (will be converted to bytes).
            **kwargs: Additional parameters:
                - labels: Dict of labels to attach to the secret

        Raises:
            SecretAccessError: If there's a permission error.
            SecretStoreError: For other GCP errors.

        Example:
            >>> store = GCPSecretManager(project_id='my-project')
            >>>
            >>> # Create or update secret
            >>> store.set_secret("api-key", "abc123", labels={"env": "prod"})
        """
        # Build the resource name for the secret
        parent = self.project_path
        secret_id = key

        # Prepare the secret data
        if isinstance(value, bytes):
            secret_data = value
        else:
            secret_data = str(value).encode("UTF-8")

        try:
            # Try to get the secret first to see if it exists
            secret_name = f"{parent}/secrets/{secret_id}"
            try:
                self.client.get_secret(request={"name": secret_name})
                secret_exists = True
            except gcp_exceptions.NotFound:
                secret_exists = False

            if not secret_exists:
                # Create the secret
                secret = {"replication": {"automatic": {}}}
                if "labels" in kwargs:
                    secret["labels"] = kwargs["labels"]

                self.client.create_secret(
                    request={
                        "parent": parent,
                        "secret_id": secret_id,
                        "secret": secret,
                    }
                )

            # Add a new version
            self.client.add_secret_version(
                request={
                    "parent": secret_name,
                    "payload": {"data": secret_data},
                }
            )

        except gcp_exceptions.PermissionDenied as e:
            raise SecretAccessError(f"Access denied setting secret '{key}': {e}")
        except Exception as e:
            raise SecretStoreError(f"Failed to set secret '{key}': {e}")

    def delete_secret(self, key: str, **kwargs) -> None:
        """Delete a secret from GCP Secret Manager.

        This permanently deletes the secret and all of its versions.

        Args:
            key: The secret name to delete.
            **kwargs: Additional parameters.

        Raises:
            SecretNotFoundError: If the secret doesn't exist.
            SecretAccessError: If there's a permission error.

        Example:
            >>> store = GCPSecretManager(project_id='my-project')
            >>> store.delete_secret("old-api-key")
        """
        name = f"{self.project_path}/secrets/{key}"

        try:
            self.client.delete_secret(request={"name": name})
        except gcp_exceptions.NotFound:
            raise SecretNotFoundError(f"Secret '{key}' not found")
        except gcp_exceptions.PermissionDenied as e:
            raise SecretAccessError(f"Access denied deleting secret '{key}': {e}")
        except Exception as e:
            raise SecretStoreError(f"Failed to delete secret '{key}': {e}")

    def list_secrets(self, prefix: Optional[str] = None, **kwargs) -> List[str]:
        """List secrets in GCP Secret Manager.

        Args:
            prefix: Optional prefix to filter secrets (applied client-side).
            **kwargs: Additional parameters.

        Returns:
            List of secret names (without the full resource path).

        Example:
            >>> store = GCPSecretManager(project_id='my-project')
            >>> all_secrets = store.list_secrets()
            >>> prod_secrets = store.list_secrets(prefix="prod-")
        """
        try:
            secrets = []
            for secret in self.client.list_secrets(request={"parent": self.project_path}):
                # Extract secret name from full path
                # Format: projects/{project}/secrets/{secret}
                secret_name = secret.name.split("/")[-1]

                if prefix is None or secret_name.startswith(prefix):
                    secrets.append(secret_name)

            return secrets

        except gcp_exceptions.PermissionDenied as e:
            raise SecretAccessError(f"Access denied listing secrets: {e}")
        except Exception as e:
            raise SecretStoreError(f"Failed to list secrets: {e}")

    def get_secret_metadata(self, key: str) -> Dict[str, Any]:
        """Get metadata about a secret.

        Args:
            key: The secret name.

        Returns:
            Dictionary with secret metadata.

        Raises:
            SecretNotFoundError: If the secret doesn't exist.

        Example:
            >>> store = GCPSecretManager(project_id='my-project')
            >>> metadata = store.get_secret_metadata("db-password")
            >>> print(f"Created: {metadata['create_time']}")
            >>> print(f"Labels: {metadata['labels']}")
        """
        name = f"{self.project_path}/secrets/{key}"

        try:
            secret = self.client.get_secret(request={"name": name})

            return {
                "name": secret.name.split("/")[-1],
                "full_name": secret.name,
                "create_time": secret.create_time,
                "labels": dict(secret.labels) if secret.labels else {},
                "replication": str(secret.replication),
            }

        except gcp_exceptions.NotFound:
            raise SecretNotFoundError(f"Secret '{key}' not found")
        except gcp_exceptions.PermissionDenied as e:
            raise SecretAccessError(f"Access denied to secret metadata '{key}': {e}")
        except Exception as e:
            raise SecretStoreError(f"Failed to get secret metadata '{key}': {e}")

    def __repr__(self) -> str:
        """String representation of the store."""
        return f"GCPSecretManager(project_id='{self.project_id}')"
