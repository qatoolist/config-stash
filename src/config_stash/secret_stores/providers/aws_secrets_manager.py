"""AWS Secrets Manager secret store provider."""

import json
from typing import Any, Dict, List, Optional

from config_stash.secret_stores.base import (
    SecretAccessError,
    SecretNotFoundError,
    SecretStore,
    SecretStoreError,
)

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False


class AWSSecretsManager(SecretStore):
    """AWS Secrets Manager secret store provider.

    This provider integrates with AWS Secrets Manager to securely retrieve secrets.
    It supports:
    - JSON and plaintext secrets
    - Secret versioning
    - Automatic JSON parsing
    - Key-based access to JSON secrets
    - Caching through boto3

    Prerequisites:
        pip install boto3

    AWS Credentials:
        Credentials are resolved using boto3's standard credential chain:
        1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
        2. ~/.aws/credentials file
        3. IAM role (when running on EC2, ECS, Lambda, etc.)

    Example:
        >>> from config_stash import Config
        >>> from config_stash.secret_stores import AWSSecretsManager, SecretResolver
        >>>
        >>> # Initialize with region
        >>> store = AWSSecretsManager(region_name='us-east-1')
        >>>
        >>> # Or with explicit credentials
        >>> store = AWSSecretsManager(
        ...     region_name='us-east-1',
        ...     aws_access_key_id='YOUR_KEY',
        ...     aws_secret_access_key='YOUR_SECRET'
        ... )
        >>>
        >>> # Use with Config
        >>> config = Config(secret_resolver=SecretResolver(store))
        >>>
        >>> # In config file: database.password = "${secret:prod/db/password}"
        >>> # Or for JSON secrets: api.key = "${secret:prod/api:key}"
    """

    def __init__(
        self,
        region_name: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_session_token: Optional[str] = None,
        endpoint_url: Optional[str] = None,
    ) -> None:
        """Initialize AWS Secrets Manager client.

        Args:
            region_name: AWS region name (default: 'us-east-1').
            aws_access_key_id: Optional AWS access key ID.
            aws_secret_access_key: Optional AWS secret access key.
            aws_session_token: Optional AWS session token for temporary credentials.
            endpoint_url: Optional custom endpoint URL (for testing with LocalStack).

        Raises:
            ImportError: If boto3 is not installed.

        Example:
            >>> # Use default credentials
            >>> store = AWSSecretsManager(region_name='eu-west-1')
            >>>
            >>> # Use explicit credentials
            >>> store = AWSSecretsManager(
            ...     region_name='us-east-1',
            ...     aws_access_key_id='AKIAIOSFODNN7EXAMPLE',
            ...     aws_secret_access_key='wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
            ... )
            >>>
            >>> # Use with LocalStack for testing
            >>> store = AWSSecretsManager(
            ...     region_name='us-east-1',
            ...     endpoint_url='http://localhost:4566'
            ... )
        """
        if not BOTO3_AVAILABLE:
            raise ImportError(
                "boto3 is required for AWSSecretsManager. " "Install it with: pip install boto3"
            )

        # Build client configuration
        client_kwargs = {"region_name": region_name}

        if aws_access_key_id and aws_secret_access_key:
            client_kwargs["aws_access_key_id"] = aws_access_key_id
            client_kwargs["aws_secret_access_key"] = aws_secret_access_key

        if aws_session_token:
            client_kwargs["aws_session_token"] = aws_session_token

        if endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url

        try:
            self.client = boto3.client("secretsmanager", **client_kwargs)
            self.region_name = region_name
        except NoCredentialsError:
            raise SecretAccessError(
                "AWS credentials not found. Please configure credentials using "
                "environment variables, ~/.aws/credentials, or IAM role."
            )
        except Exception as e:
            raise SecretStoreError(f"Failed to initialize AWS Secrets Manager client: {e}")

    def get_secret(self, key: str, version: Optional[str] = None, **kwargs) -> Any:
        """Retrieve a secret from AWS Secrets Manager.

        Args:
            key: The secret name or ARN. Can include ":json_key" suffix to extract
                a specific key from JSON secrets (e.g., "my-secret:database_password").
            version: Optional version ID or version stage (e.g., "AWSCURRENT", "AWSPENDING").
            **kwargs: Additional parameters for get_secret_value API call.

        Returns:
            The secret value. For JSON secrets, returns the parsed dict.
            For secrets with ":key" suffix, returns the specific value.

        Raises:
            SecretNotFoundError: If the secret doesn't exist.
            SecretAccessError: If there's a permission error.
            SecretStoreError: For other AWS errors.

        Example:
            >>> store = AWSSecretsManager(region_name='us-east-1')
            >>>
            >>> # Get plaintext secret
            >>> password = store.get_secret("prod/db/password")
            >>>
            >>> # Get JSON secret
            >>> config = store.get_secret("prod/api/config")
            >>> # Returns: {"key": "abc123", "endpoint": "https://api.example.com"}
            >>>
            >>> # Get specific version
            >>> old_key = store.get_secret("api/key", version="v1-guid-here")
        """
        # Parse key and json_key from format "secret_name:json_key"
        if ":" in key:
            secret_name, json_key = key.split(":", 1)
        else:
            secret_name = key
            json_key = None

        # Build request parameters
        request_params = {"SecretId": secret_name}

        if version:
            # Check if version is a stage or version ID
            if (
                version.startswith("AWSCURRENT")
                or version.startswith("AWSPENDING")
                or version.startswith("AWSPREVIOUS")
            ):
                request_params["VersionStage"] = version
            else:
                request_params["VersionId"] = version

        request_params.update(kwargs)

        try:
            response = self.client.get_secret_value(**request_params)

            # Extract secret value
            if "SecretString" in response:
                secret_value = response["SecretString"]

                # Try to parse as JSON
                try:
                    parsed = json.loads(secret_value)
                    # If json_key is specified, extract that key
                    if json_key:
                        if isinstance(parsed, dict) and json_key in parsed:
                            return parsed[json_key]
                        else:
                            raise SecretNotFoundError(
                                f"Key '{json_key}' not found in JSON secret '{secret_name}'"
                            )
                    return parsed
                except json.JSONDecodeError:
                    # Not JSON, return as string
                    return secret_value
            elif "SecretBinary" in response:
                # Binary secrets
                return response["SecretBinary"]
            else:
                raise SecretStoreError(
                    f"Secret '{secret_name}' has no SecretString or SecretBinary"
                )

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")

            if error_code == "ResourceNotFoundException":
                raise SecretNotFoundError(
                    f"Secret '{secret_name}' not found in AWS Secrets Manager "
                    f"(region: {self.region_name})"
                )
            elif error_code in ("AccessDeniedException", "InvalidRequestException"):
                raise SecretAccessError(f"Access denied to secret '{secret_name}': {e}")
            else:
                raise SecretStoreError(
                    f"AWS Secrets Manager error for '{secret_name}': {error_code} - {e}"
                )
        except BotoCoreError as e:
            raise SecretStoreError(f"AWS SDK error: {e}")

    def set_secret(self, key: str, value: Any, **kwargs) -> None:
        """Create or update a secret in AWS Secrets Manager.

        Args:
            key: The secret name.
            value: The secret value. Dicts will be JSON-encoded automatically.
            **kwargs: Additional parameters for create_secret/update_secret:
                - Description: Secret description
                - KmsKeyId: KMS key for encryption
                - Tags: List of tags

        Raises:
            SecretAccessError: If there's a permission error.
            SecretStoreError: For other AWS errors.

        Example:
            >>> store = AWSSecretsManager(region_name='us-east-1')
            >>>
            >>> # Store plaintext secret
            >>> store.set_secret("dev/api/key", "abc123")
            >>>
            >>> # Store JSON secret
            >>> store.set_secret("dev/db/config", {
            ...     "host": "localhost",
            ...     "port": 5432,
            ...     "password": "secret"
            ... })
        """
        # Convert dict to JSON string
        if isinstance(value, dict):
            secret_string = json.dumps(value)
        else:
            secret_string = str(value)

        try:
            # Try to update existing secret
            update_params = {"SecretId": key, "SecretString": secret_string}
            update_params.update({k: v for k, v in kwargs.items() if k in ["Description"]})

            self.client.update_secret(**update_params)

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")

            if error_code == "ResourceNotFoundException":
                # Secret doesn't exist, create it
                create_params = {"Name": key, "SecretString": secret_string}
                create_params.update(kwargs)

                try:
                    self.client.create_secret(**create_params)
                except ClientError as create_error:
                    error_code = create_error.response.get("Error", {}).get("Code", "")
                    if error_code in ("AccessDeniedException", "InvalidRequestException"):
                        raise SecretAccessError(
                            f"Access denied creating secret '{key}': {create_error}"
                        )
                    else:
                        raise SecretStoreError(f"Failed to create secret '{key}': {create_error}")
            elif error_code in ("AccessDeniedException", "InvalidRequestException"):
                raise SecretAccessError(f"Access denied updating secret '{key}': {e}")
            else:
                raise SecretStoreError(f"Failed to update secret '{key}': {e}")

    def delete_secret(self, key: str, **kwargs) -> None:
        """Delete a secret from AWS Secrets Manager.

        Args:
            key: The secret name to delete.
            **kwargs: Additional parameters:
                - ForceDeleteWithoutRecovery: Skip recovery window (default: False)
                - RecoveryWindowInDays: Recovery period in days (7-30, default: 30)

        Raises:
            SecretNotFoundError: If the secret doesn't exist.
            SecretAccessError: If there's a permission error.
            SecretStoreError: For other AWS errors.

        Example:
            >>> store = AWSSecretsManager(region_name='us-east-1')
            >>>
            >>> # Delete with recovery window
            >>> store.delete_secret("old/api/key", RecoveryWindowInDays=7)
            >>>
            >>> # Force delete immediately (no recovery)
            >>> store.delete_secret("temp/key", ForceDeleteWithoutRecovery=True)
        """
        delete_params = {"SecretId": key}
        delete_params.update(kwargs)

        try:
            self.client.delete_secret(**delete_params)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")

            if error_code == "ResourceNotFoundException":
                raise SecretNotFoundError(f"Secret '{key}' not found")
            elif error_code in ("AccessDeniedException", "InvalidRequestException"):
                raise SecretAccessError(f"Access denied deleting secret '{key}': {e}")
            else:
                raise SecretStoreError(f"Failed to delete secret '{key}': {e}")

    def list_secrets(self, prefix: Optional[str] = None, **kwargs) -> List[str]:
        """List secrets in AWS Secrets Manager.

        Args:
            prefix: Optional name prefix to filter secrets.
            **kwargs: Additional parameters for list_secrets API call.

        Returns:
            List of secret names.

        Raises:
            SecretAccessError: If there's a permission error.
            SecretStoreError: For other AWS errors.

        Example:
            >>> store = AWSSecretsManager(region_name='us-east-1')
            >>>
            >>> # List all secrets
            >>> all_secrets = store.list_secrets()
            >>>
            >>> # List secrets with prefix
            >>> prod_secrets = store.list_secrets(prefix="prod/")
        """
        secrets = []
        next_token = None

        try:
            while True:
                list_params = kwargs.copy()
                if next_token:
                    list_params["NextToken"] = next_token

                response = self.client.list_secrets(**list_params)

                for secret in response.get("SecretList", []):
                    name = secret.get("Name", "")
                    if prefix is None or name.startswith(prefix):
                        secrets.append(name)

                next_token = response.get("NextToken")
                if not next_token:
                    break

            return secrets

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ("AccessDeniedException", "InvalidRequestException"):
                raise SecretAccessError(f"Access denied listing secrets: {e}")
            else:
                raise SecretStoreError(f"Failed to list secrets: {e}")

    def get_secret_metadata(self, key: str) -> Dict[str, Any]:
        """Get metadata about a secret.

        Args:
            key: The secret name.

        Returns:
            Dictionary with secret metadata.

        Raises:
            SecretNotFoundError: If the secret doesn't exist.
            SecretAccessError: If there's a permission error.

        Example:
            >>> store = AWSSecretsManager(region_name='us-east-1')
            >>> metadata = store.get_secret_metadata("prod/db/password")
            >>> print(f"Created: {metadata['CreatedDate']}")
            >>> print(f"Version: {metadata['VersionIdsToStages']}")
        """
        try:
            response = self.client.describe_secret(SecretId=key)

            return {
                "Name": response.get("Name"),
                "ARN": response.get("ARN"),
                "Description": response.get("Description", ""),
                "CreatedDate": response.get("CreatedDate"),
                "LastChangedDate": response.get("LastChangedDate"),
                "LastAccessedDate": response.get("LastAccessedDate"),
                "VersionIdsToStages": response.get("VersionIdsToStages", {}),
                "Tags": response.get("Tags", []),
            }

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "ResourceNotFoundException":
                raise SecretNotFoundError(f"Secret '{key}' not found")
            elif error_code in ("AccessDeniedException", "InvalidRequestException"):
                raise SecretAccessError(f"Access denied to secret metadata '{key}': {e}")
            else:
                raise SecretStoreError(f"Failed to get secret metadata '{key}': {e}")

    def __repr__(self) -> str:
        """String representation of the store."""
        return f"AWSSecretsManager(region={self.region_name})"
