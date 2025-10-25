"""AWS authentication for Vault."""

from typing import Any, Optional

from config_stash.secret_stores.vault_auth.base import (
    VaultAuthMethod,
    VaultAuthenticationError,
)


class AWSAuth(VaultAuthMethod):
    """AWS authentication for Vault.

    Use this when running on AWS (EC2, ECS, Lambda) to authenticate
    using AWS credentials or IAM roles.

    Example:
        >>> from config_stash.secret_stores.vault_auth import AWSAuth
        >>> from config_stash.secret_stores import HashiCorpVault
        >>>
        >>> # EC2 instance
        >>> auth = AWSAuth(role='myapp-ec2-role', auth_type='ec2')
        >>> vault = HashiCorpVault(
        ...     url='https://vault.example.com',
        ...     auth_method=auth
        ... )
        >>>
        >>> # IAM role
        >>> auth = AWSAuth(role='myapp-iam-role', auth_type='iam')
    """

    def __init__(
        self,
        role: str,
        auth_type: str = "iam",
        mount_point: str = "aws",
        nonce: Optional[str] = None,
    ):
        """Initialize AWS authentication.

        Args:
            role: Vault AWS role name
            auth_type: AWS auth type ('ec2' or 'iam', default: 'iam')
            mount_point: Auth mount point (default: 'aws')
            nonce: Optional nonce for EC2 auth (prevents replay attacks)

        Example:
            >>> # IAM role (for ECS, Lambda, EC2 with IAM role)
            >>> auth = AWSAuth(role='myapp', auth_type='iam')
            >>>
            >>> # EC2 instance
            >>> auth = AWSAuth(role='myapp', auth_type='ec2')
        """
        self.role = role
        self.auth_type = auth_type
        self.mount_point_value = mount_point
        self.nonce = nonce

    def authenticate(self, client: Any) -> str:
        """Authenticate using AWS credentials.

        Args:
            client: hvac.Client instance

        Returns:
            Vault client token

        Raises:
            VaultAuthenticationError: If AWS auth fails
        """
        try:
            if self.auth_type == "ec2":
                response = client.auth.aws.ec2_login(
                    role=self.role,
                    nonce=self.nonce,
                    mount_point=self.mount_point_value,
                )
            elif self.auth_type == "iam":
                response = client.auth.aws.iam_login(
                    role=self.role,
                    mount_point=self.mount_point_value,
                )
            else:
                raise VaultAuthenticationError(
                    f"Unknown AWS auth type: {self.auth_type}. "
                    f"Must be 'ec2' or 'iam'"
                )

            return response["auth"]["client_token"]

        except Exception as e:
            raise VaultAuthenticationError(
                f"AWS authentication failed: {e}"
            )

    def get_mount_point(self) -> str:
        """Get the AWS auth mount point."""
        return self.mount_point_value
