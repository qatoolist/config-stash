# pyright: reportPossiblyUnboundVariable=false
# pyright: reportMissingImports=false
"""Loader for AWS Systems Manager Parameter Store."""

import logging
import os
from typing import Any, Dict, Optional

from config_stash.exceptions import ConfigLoadError
from config_stash.loaders.loader import Loader
from config_stash.utils.type_coercion import parse_scalar_value

logger = logging.getLogger(__name__)


class SSMLoader(Loader):
    """Load configuration from AWS Systems Manager Parameter Store.

    SSMLoader fetches parameters stored under a given path prefix in AWS
    SSM Parameter Store and converts them into a nested Python dictionary.
    For example, parameters stored at ``/myapp/production/database/host``
    and ``/myapp/production/database/port`` with a ``path_prefix`` of
    ``/myapp/production/`` produce::

        {"database": {"host": "db.example.com", "port": 5432}}

    Authentication can be provided explicitly via constructor arguments, or
    implicitly through IAM roles, environment variables
    (``AWS_ACCESS_KEY_ID``, ``AWS_SECRET_ACCESS_KEY``, ``AWS_DEFAULT_REGION``),
    or the default boto3 credential chain.

    String values are automatically coerced to appropriate Python types
    (int, float, bool) via ``parse_scalar_value``.

    Attributes:
        source: The SSM path prefix used as the configuration source.
        path_prefix: The SSM path prefix to fetch parameters from.
        decrypt: Whether to decrypt SecureString parameters.
        aws_region: AWS region name.
        aws_access_key_id: AWS access key ID (may be None for IAM).
        aws_secret_access_key: AWS secret access key (may be None for IAM).
        config: The loaded configuration dictionary.

    Example:
        >>> from config_stash.loaders.ssm_loader import SSMLoader
        >>> loader = SSMLoader(
        ...     path_prefix="/myapp/production/",
        ...     decrypt=True,
        ...     aws_region="us-west-2",
        ... )
        >>> config_dict = loader.load()
        >>> print(config_dict["database"]["host"])

    Note:
        Requires the ``boto3`` package. Install it with::

            pip install boto3
    """

    def __init__(
        self,
        path_prefix: str,
        decrypt: bool = True,
        aws_region: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ) -> None:
        """Initialize SSM Parameter Store loader.

        Args:
            path_prefix: SSM path prefix to fetch parameters from (e.g.,
                ``/myapp/production/``). A trailing slash is added
                automatically if not present.
            decrypt: Whether to decrypt SecureString parameters.
                Defaults to ``True``.
            aws_region: AWS region name. Falls back to the
                ``AWS_DEFAULT_REGION`` environment variable, then
                ``"us-east-1"``.
            aws_access_key_id: AWS access key ID. Falls back to the
                ``AWS_ACCESS_KEY_ID`` environment variable or IAM role.
            aws_secret_access_key: AWS secret access key. Falls back to the
                ``AWS_SECRET_ACCESS_KEY`` environment variable or IAM role.
        """
        # Ensure trailing slash on prefix
        if not path_prefix.endswith("/"):
            path_prefix = path_prefix + "/"
        super().__init__(source=path_prefix)
        self.path_prefix = path_prefix
        self.decrypt = decrypt
        self.aws_region = (
            aws_region or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"
        )
        self.aws_access_key_id = aws_access_key_id or os.environ.get(
            "AWS_ACCESS_KEY_ID"
        )
        self.aws_secret_access_key = aws_secret_access_key or os.environ.get(
            "AWS_SECRET_ACCESS_KEY"
        )

    def load(self) -> Optional[Dict[str, Any]]:
        """Load configuration from AWS SSM Parameter Store.

        Fetches all parameters under ``path_prefix`` using the SSM
        ``get_parameters_by_path`` API with automatic pagination. Each
        parameter's path (relative to the prefix) is split into nested
        dictionary keys, and string values are coerced to native Python
        types where possible.

        Returns:
            Dictionary containing the loaded configuration, or ``None``
            if no parameters were found under the prefix.

        Raises:
            ImportError: If ``boto3`` is not installed.
            ConfigLoadError: If the SSM API call fails.

        Example:
            >>> loader = SSMLoader("/myapp/production/")
            >>> config = loader.load()
        """
        try:
            import boto3  # type: ignore[import-untyped]
        except ImportError:
            raise ImportError(
                "boto3 is required for SSM Parameter Store loading. "
                "Install with: pip install boto3"
            )

        try:
            logger.info(
                f"Loading configuration from SSM Parameter Store: {self.path_prefix}"
            )

            # Create SSM client
            client_kwargs: Dict[str, Any] = {
                "region_name": self.aws_region,
            }
            if self.aws_access_key_id and self.aws_secret_access_key:
                client_kwargs["aws_access_key_id"] = self.aws_access_key_id
                client_kwargs["aws_secret_access_key"] = self.aws_secret_access_key

            ssm_client = boto3.client("ssm", **client_kwargs)

            # Fetch all parameters under the path prefix with pagination
            parameters = []
            paginator = ssm_client.get_paginator("get_parameters_by_path")
            page_iterator = paginator.paginate(
                Path=self.path_prefix,
                Recursive=True,
                WithDecryption=self.decrypt,
            )

            for page in page_iterator:
                parameters.extend(page.get("Parameters", []))

            if not parameters:
                logger.info(f"No parameters found under {self.path_prefix}")
                return None

            # Convert flat SSM parameters to nested dict
            result: Dict[str, Any] = {}
            for param in parameters:
                name = param["Name"]
                value = param["Value"]

                # Strip the path prefix to get the relative key
                relative_key = name[len(self.path_prefix) :]

                # Apply type coercion
                typed_value = parse_scalar_value(value)

                # Split into nested keys
                keys = relative_key.strip("/").split("/")
                self._set_nested(result, keys, typed_value)

            self.config = result
            logger.info(
                f"Successfully loaded {len(parameters)} parameters "
                f"from SSM: {self.path_prefix}"
            )
            return self.config

        except ImportError:
            raise
        except ConfigLoadError:
            raise
        except Exception as e:
            logger.error(f"Failed to load configuration from SSM Parameter Store: {e}")
            raise ConfigLoadError(
                f"Failed to load SSM configuration from {self.path_prefix}",
                source=self.path_prefix,
                loader_type=self.__class__.__name__,
                original_error=e,
            ) from e

    @staticmethod
    def _set_nested(d: Dict[str, Any], keys: list, value: Any) -> None:
        """Set a value in a nested dictionary using a list of keys.

        Creates intermediate dictionaries as needed.

        Args:
            d: The dictionary to modify.
            keys: List of keys representing the path.
            value: The value to set at the final key.

        Example:
            >>> d = {}
            >>> SSMLoader._set_nested(d, ["database", "host"], "localhost")
            >>> d
            {'database': {'host': 'localhost'}}
        """
        for key in keys[:-1]:
            if key not in d or not isinstance(d[key], dict):
                d[key] = {}
            d = d[key]
        d[keys[-1]] = value
