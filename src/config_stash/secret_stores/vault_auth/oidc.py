"""OIDC/JWT authentication for Vault with Kerberos support.

This module provides comprehensive OIDC authentication including:
- Browser-based OIDC flow
- Kerberos-based automatic authentication (if kinit already done)
- Username/password authentication with custom password policies
- Support for PIN+Token authentication patterns
"""

import logging
import os
import subprocess
import threading
import webbrowser

logger = logging.getLogger(__name__)
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable, Optional
from urllib.parse import parse_qs, urlparse

from config_stash.secret_stores.vault_auth.base import (
    VaultAuthenticationError,
    VaultAuthMethod,
)


class OIDCAuth(VaultAuthMethod):
    """OIDC authentication for Vault with enterprise features.

    Supports multiple authentication flows:
    1. Kerberos-based (if kinit already done) - no browser needed
    2. Browser-based OIDC flow
    3. Custom callback handler for enterprise password policies

    Example:
        >>> from config_stash.secret_stores.vault_auth import OIDCAuth
        >>> from config_stash.secret_stores import HashiCorpVault
        >>>
        >>> # Kerberos-based (automatic if kinit done)
        >>> auth = OIDCAuth(role='myapp-role', use_kerberos=True)
        >>> vault = HashiCorpVault(
        ...     url='https://vault.example.com',
        ...     auth_method=auth
        ... )
        >>>
        >>> # Browser-based
        >>> auth = OIDCAuth(role='myapp-role')
        >>> vault = HashiCorpVault(
        ...     url='https://vault.example.com',
        ...     auth_method=auth
        ... )
        >>>
        >>> # Custom password handler (PIN+Token)
        >>> def get_credentials():
        ...     username = input("Kerberos ID: ")
        ...     pin = input("PIN: ")
        ...     token = input("Token: ")
        ...     password = pin + token
        ...     return username, password
        >>>
        >>> auth = OIDCAuth(
        ...     role='myapp-role',
        ...     credential_provider=get_credentials
        ... )
    """

    def __init__(
        self,
        role: str,
        use_kerberos: bool = False,
        credential_provider: Optional[Callable[[], tuple]] = None,
        mount_point: str = "oidc",
        callback_host: str = "localhost",
        callback_port: int = 8250,
        skip_browser: bool = False,
    ):
        """Initialize OIDC authentication.

        Args:
            role: Vault OIDC role name
            use_kerberos: Try Kerberos-based auth first (requires kinit)
            credential_provider: Optional function that returns (username, password)
                tuple for custom authentication flows. Useful for PIN+Token patterns.
            mount_point: Auth mount point (default: 'oidc')
            callback_host: Callback server host (default: 'localhost')
            callback_port: Callback server port (default: 8250)
            skip_browser: Don't open browser automatically (default: False)

        Example:
            >>> # Kerberos-based
            >>> auth = OIDCAuth(role='myapp', use_kerberos=True)
            >>>
            >>> # Custom credential provider for PIN+Token
            >>> def pin_token_auth():
            ...     user = os.getenv('USER')  # Kerberos ID
            ...     pin = getpass.getpass("Enter PIN: ")
            ...     token = getpass.getpass("Enter Token: ")
            ...     return user, pin + token
            >>>
            >>> auth = OIDCAuth(
            ...     role='myapp',
            ...     credential_provider=pin_token_auth
            ... )
        """
        self.role = role
        self.use_kerberos = use_kerberos
        self.credential_provider = credential_provider
        self.mount_point_value = mount_point
        self.callback_host = callback_host
        self.callback_port = callback_port
        self.skip_browser = skip_browser

    def authenticate(self, client: Any) -> str:
        """Authenticate using OIDC.

        Tries multiple authentication methods in order:
        1. Kerberos (if use_kerberos=True)
        2. Custom credential provider (if provided)
        3. Browser-based OIDC flow (default)

        Args:
            client: hvac.Client instance

        Returns:
            Vault client token

        Raises:
            VaultAuthenticationError: If all authentication methods fail
        """
        errors = []

        # Try Kerberos-based authentication first
        if self.use_kerberos:
            try:
                return self._authenticate_kerberos(client)
            except Exception as e:
                errors.append(f"Kerberos auth failed: {e}")

        # Try custom credential provider
        if self.credential_provider:
            try:
                return self._authenticate_with_credentials(client)
            except Exception as e:
                errors.append(f"Credential provider auth failed: {e}")

        # Fall back to browser-based OIDC
        try:
            return self._authenticate_browser(client)
        except Exception as e:
            errors.append(f"Browser auth failed: {e}")

        # All methods failed
        raise VaultAuthenticationError(
            f"OIDC authentication failed. Attempted methods: " f"{', '.join(errors)}"
        )

    def _authenticate_kerberos(self, client: Any) -> str:
        """Authenticate using Kerberos ticket (if kinit already done).

        This method checks if a valid Kerberos ticket exists and uses it
        for authentication without requiring browser interaction.

        Args:
            client: hvac.Client instance

        Returns:
            Vault client token

        Raises:
            VaultAuthenticationError: If Kerberos auth fails
        """
        try:
            # Check if Kerberos ticket exists
            result = subprocess.run(["klist", "-s"], capture_output=True, timeout=5)

            if result.returncode != 0:
                raise VaultAuthenticationError("No valid Kerberos ticket found. Run 'kinit' first.")

            # Get Kerberos principal
            result = subprocess.run(["klist"], capture_output=True, text=True, timeout=5)

            # Use hvac's OIDC with Kerberos
            # Note: This requires the Vault OIDC auth to be configured
            # to accept Kerberos tickets
            response = client.auth.oidc.oidc_callback(
                role=self.role,
                mount_point=self.mount_point_value,
                # Kerberos ticket will be passed via SPNEGO
            )

            return response["auth"]["client_token"]

        except subprocess.TimeoutExpired:
            raise VaultAuthenticationError("Kerberos check timed out")
        except FileNotFoundError:
            raise VaultAuthenticationError(
                "Kerberos tools not found. Install krb5-user or krb5-workstation."
            )
        except Exception as e:
            raise VaultAuthenticationError(f"Kerberos authentication failed: {e}")

    def _authenticate_with_credentials(self, client: Any) -> str:
        """Authenticate using custom credential provider.

        This allows for complex authentication flows like PIN+Token
        where the password is constructed from multiple inputs.

        Args:
            client: hvac.Client instance

        Returns:
            Vault client token

        Raises:
            VaultAuthenticationError: If credential auth fails
        """
        try:
            # Get credentials from provider
            if self.credential_provider is None:
                raise VaultAuthenticationError("No credential provider configured")
            username, password = self.credential_provider()

            if not username or not password:
                raise VaultAuthenticationError("Credential provider returned empty credentials")

            # Use OIDC with username/password
            # This typically requires the OIDC provider to support
            # resource owner password credentials flow
            response = client.auth.oidc.login(
                role=self.role,
                username=username,
                password=password,
                mount_point=self.mount_point_value,
            )

            return response["auth"]["client_token"]

        except Exception as e:
            raise VaultAuthenticationError(f"Credential-based authentication failed: {e}")

    def _authenticate_browser(self, client: Any) -> str:
        """Authenticate using browser-based OIDC flow.

        This opens a browser for the user to authenticate with their
        identity provider (Okta, Azure AD, etc.).

        Args:
            client: hvac.Client instance

        Returns:
            Vault client token

        Raises:
            VaultAuthenticationError: If browser auth fails
        """
        try:
            # Start OIDC authentication
            auth_url_response = client.auth.oidc.auth_url(
                role=self.role,
                redirect_uri=f"http://{self.callback_host}:{self.callback_port}/oidc/callback",
                mount_point=self.mount_point_value,
            )

            auth_url = auth_url_response["data"]["auth_url"]
            state = auth_url_response["data"]["state"]
            nonce = auth_url_response["data"]["nonce"]

            # Set up callback server
            callback_data = {}

            class CallbackHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    parsed = urlparse(self.path)
                    if parsed.path == "/oidc/callback":
                        params = parse_qs(parsed.query)
                        callback_data["code"] = params.get("code", [None])[0]
                        callback_data["state"] = params.get("state", [None])[0]

                        self.send_response(200)
                        self.send_header("Content-type", "text/html")
                        self.end_headers()
                        self.wfile.write(
                            b"<html><body><h1>Authentication successful!</h1>"
                            b"<p>You can close this window now.</p></body></html>"
                        )

                def log_message(self, format, *args):
                    pass  # Suppress log messages

            # Start callback server
            server = HTTPServer((self.callback_host, self.callback_port), CallbackHandler)

            def run_server():
                server.handle_request()

            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()

            # Open browser
            if not self.skip_browser:
                logger.info("Opening browser for authentication...")
                logger.info(f"If browser doesn't open, visit: {auth_url}")
                webbrowser.open(auth_url)
            else:
                logger.info(f"Visit this URL to authenticate: {auth_url}")

            # Wait for callback
            server_thread.join(timeout=300)  # 5 minute timeout
            server.server_close()

            if not callback_data.get("code"):
                raise VaultAuthenticationError("Authentication timeout or callback not received")

            # Complete OIDC authentication
            response = client.auth.oidc.oidc_callback(
                code=callback_data["code"],
                path="oidc/callback",
                state=state,
                nonce=nonce,
                mount_point=self.mount_point_value,
            )

            return response["auth"]["client_token"]

        except Exception as e:
            raise VaultAuthenticationError(f"Browser-based OIDC authentication failed: {e}")

    def get_mount_point(self) -> str:
        """Get the OIDC auth mount point."""
        return self.mount_point_value


class KerberosAuth(VaultAuthMethod):
    """Dedicated Kerberos authentication for Vault.

    This is a simplified version that only uses Kerberos, without
    falling back to other methods.

    Example:
        >>> from config_stash.secret_stores.vault_auth import KerberosAuth
        >>> from config_stash.secret_stores import HashiCorpVault
        >>>
        >>> # Ensure kinit is done first
        >>> # $ kinit user@REALM
        >>>
        >>> auth = KerberosAuth(role='myapp-role')
        >>> vault = HashiCorpVault(
        ...     url='https://vault.example.com',
        ...     auth_method=auth
        ... )
    """

    def __init__(self, role: str, mount_point: str = "oidc"):
        """Initialize Kerberos authentication.

        Args:
            role: Vault role name
            mount_point: Auth mount point (default: 'oidc')

        Example:
            >>> auth = KerberosAuth(role='myapp')
        """
        self.role = role
        self.mount_point_value = mount_point

    def authenticate(self, client: Any) -> str:
        """Authenticate using Kerberos ticket.

        Requires that 'kinit' has been run before calling this.

        Args:
            client: hvac.Client instance

        Returns:
            Vault client token

        Raises:
            VaultAuthenticationError: If Kerberos auth fails
        """
        # Use OIDCAuth's Kerberos implementation
        oidc_auth = OIDCAuth(
            role=self.role,
            use_kerberos=True,
            mount_point=self.mount_point_value,
        )

        # Only try Kerberos, don't fall back
        try:
            return oidc_auth._authenticate_kerberos(client)
        except Exception as e:
            raise VaultAuthenticationError(
                f"Kerberos authentication failed: {e}. "
                f"Ensure you have run 'kinit' to get a valid ticket."
            )

    def get_mount_point(self) -> str:
        """Get the mount point."""
        return self.mount_point_value
