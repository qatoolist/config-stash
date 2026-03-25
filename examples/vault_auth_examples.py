# pyright: basic
"""Comprehensive examples of HashiCorp Vault authentication methods.

This demonstrates all supported authentication methods including:
- OIDC with Kerberos support
- LDAP with complex password policies (PIN+Token)
- JWT, Kubernetes, AWS, Azure, GCP
- Token and AppRole (legacy)
"""

import getpass
import os
import tempfile


def example_oidc_with_kerberos():
    """Example: OIDC authentication with Kerberos (no browser needed)."""
    print("\n" + "="*70)
    print("Example 1: OIDC Authentication with Kerberos")
    print("="*70)

    print("""
OIDC with Kerberos allows automatic authentication if you've already
done 'kinit' to get a Kerberos ticket. No browser interaction needed!

Prerequisites:
1. Install hvac: pip install hvac
2. Run kinit: kinit user@REALM
3. Configure Vault OIDC auth with Kerberos support

Usage:
    from config_stash import Config
    from config_stash.secret_stores import HashiCorpVault
    from config_stash.secret_stores.vault_auth import OIDCAuth

    # Automatic Kerberos-based auth (if kinit done)
    auth = OIDCAuth(
        role='myapp-role',
        use_kerberos=True  # Try Kerberos first
    )

    vault = HashiCorpVault(
        url='https://vault.example.com',
        auth_method=auth,
        mount_point='secret',
        kv_version=2
    )

    # Use with Config
    from config_stash.secret_stores import SecretResolver
    config = Config(
        env='production',
        secret_resolver=SecretResolver(vault)
    )

Benefits:
- No browser pop-up
- Works in automated scripts
- Uses existing Kerberos ticket
- Falls back to browser if Kerberos fails
""")


def example_oidc_browser():
    """Example: OIDC authentication with browser flow."""
    print("\n" + "="*70)
    print("Example 2: OIDC Authentication with Browser")
    print("="*70)

    print("""
Standard OIDC authentication that opens a browser for login.
Works with any OIDC provider (Okta, Azure AD, Google, etc.)

Usage:
    from config_stash.secret_stores import HashiCorpVault
    from config_stash.secret_stores.vault_auth import OIDCAuth

    # Browser-based OIDC
    auth = OIDCAuth(
        role='myapp-role',
        callback_port=8250,
        skip_browser=False  # Automatically open browser
    )

    vault = HashiCorpVault(
        url='https://vault.example.com',
        auth_method=auth
    )

What happens:
1. Opens browser to your OIDC provider
2. You authenticate with username/password or SSO
3. Browser redirects back to local callback
4. Vault token is obtained automatically
""")


def example_ldap_pin_token():
    """Example: LDAP authentication with PIN+Token password policy."""
    print("\n" + "="*70)
    print("Example 3: LDAP Authentication with PIN+Token")
    print("="*70)

    print("""
Many organizations use complex password policies where the password
is constructed from multiple inputs (e.g., PIN + Token from RSA/Duo).

Usage:
    from config_stash.secret_stores import HashiCorpVault
    from config_stash.secret_stores.vault_auth import LDAPAuth
    import getpass

    # Custom password provider for PIN+Token
    def get_pin_token_password():
        pin = getpass.getpass("Enter your PIN: ")
        token = getpass.getpass("Enter your Token: ")
        return pin + token  # Combine PIN and Token

    auth = LDAPAuth(
        username='john.doe',  # Or use os.getenv('USER')
        password_provider=get_pin_token_password
    )

    vault = HashiCorpVault(
        url='https://vault.example.com',
        auth_method=auth
    )

Supports any custom password construction:
- PIN + Token
- Password + OTP
- Password + Biometric code
- Any custom logic you need
""")


def example_ldap_kerberos_id():
    """Example: LDAP with Kerberos ID and PIN+Token."""
    print("\n" + "="*70)
    print("Example 4: LDAP with Kerberos ID Username")
    print("="*70)

    print("""
Use your Kerberos ID as username with custom password policy.

Usage:
    from config_stash.secret_stores import HashiCorpVault
    from config_stash.secret_stores.vault_auth import LDAPAuth
    import getpass
    import os

    def get_credentials_from_org_policy():
        # Use Kerberos ID as username
        username = os.getenv('USER')  # or getpass.getuser()

        # Custom password policy (PIN+Token, Password+OTP, etc.)
        print(f"Authenticating as: {username}")
        pin = getpass.getpass("Enter PIN: ")
        token = getpass.getpass("Enter Token from authenticator: ")

        # Your organization's password policy
        password = pin + token  # Or any other combination

        return username, password

    # Create auth with custom credential provider
    def cred_provider():
        username, password = get_credentials_from_org_policy()
        # LDAPAuth expects just password from password_provider
        # So we need to set username separately
        return password

    username, _ = get_credentials_from_org_policy()
    auth = LDAPAuth(
        username=username,
        password_provider=cred_provider
    )

    vault = HashiCorpVault(
        url='https://vault.example.com',
        auth_method=auth
    )

    # Or use the simplified approach:
    def get_pin_token():
        pin = getpass.getpass("PIN: ")
        token = getpass.getpass("Token: ")
        return pin + token

    auth = LDAPAuth(
        username=os.getenv('USER'),  # Kerberos ID
        password_provider=get_pin_token
    )
""")


def example_kubernetes():
    """Example: Kubernetes authentication."""
    print("\n" + "="*70)
    print("Example 5: Kubernetes Authentication")
    print("="*70)

    print("""
Automatic authentication when running inside Kubernetes pods.

Usage:
    from config_stash.secret_stores import HashiCorpVault
    from config_stash.secret_stores.vault_auth import KubernetesAuth

    # Automatic (reads service account token)
    auth = KubernetesAuth(role='myapp-role')

    vault = HashiCorpVault(
        url='https://vault.example.com',
        auth_method=auth
    )

    # In your Kubernetes deployment:
    # apiVersion: apps/v1
    # kind: Deployment
    # spec:
    #   template:
    #     spec:
    #       serviceAccountName: myapp-sa
    #       containers:
    #       - name: myapp
    #         env:
    #         - name: VAULT_ADDR
    #           value: "https://vault.example.com"

The Kubernetes service account token is automatically mounted at:
/var/run/secrets/kubernetes.io/serviceaccount/token
""")


def example_aws():
    """Example: AWS authentication."""
    print("\n" + "="*70)
    print("Example 6: AWS Authentication")
    print("="*70)

    print("""
Automatic authentication when running on AWS (EC2, ECS, Lambda).

Usage:
    from config_stash.secret_stores import HashiCorpVault
    from config_stash.secret_stores.vault_auth import AWSAuth

    # For IAM role (ECS, Lambda, EC2 with IAM role)
    auth = AWSAuth(
        role='myapp-role',
        auth_type='iam'
    )

    # For EC2 instance
    auth = AWSAuth(
        role='myapp-ec2-role',
        auth_type='ec2'
    )

    vault = HashiCorpVault(
        url='https://vault.example.com',
        auth_method=auth
    )

Vault will verify:
- IAM credentials from instance metadata
- EC2 instance identity document
""")


def example_jwt():
    """Example: JWT authentication."""
    print("\n" + "="*70)
    print("Example 7: JWT Authentication")
    print("="*70)

    print("""
Use JWT tokens from external sources (CI/CD, service mesh, etc.).

Usage:
    from config_stash.secret_stores import HashiCorpVault
    from config_stash.secret_stores.vault_auth import JWTAuth
    import os

    # JWT from environment or file
    jwt_token = os.getenv('JWT_TOKEN')
    # Or: jwt_token = open('/path/to/jwt').read().strip()

    auth = JWTAuth(
        role='myapp-role',
        jwt=jwt_token
    )

    vault = HashiCorpVault(
        url='https://vault.example.com',
        auth_method=auth
    )

Common JWT sources:
- GitLab CI: CI_JOB_JWT
- GitHub Actions: ACTIONS_ID_TOKEN_REQUEST_TOKEN
- Service mesh (Istio, Linkerd): /var/run/secrets/tokens/vault-token
""")


def example_multi_auth_fallback():
    """Example: Multiple authentication methods with fallback."""
    print("\n" + "="*70)
    print("Example 8: Multiple Authentication with Fallback")
    print("="*70)

    print("""
Try multiple authentication methods in order of preference.

Usage:
    from config_stash.secret_stores import HashiCorpVault
    from config_stash.secret_stores.vault_auth import (
        OIDCAuth, LDAPAuth, TokenAuth
    )
    import os

    def get_vault_store():
        vault_url = 'https://vault.example.com'

        # Try OIDC with Kerberos first (if kinit done)
        if os.system('klist -s') == 0:  # Check for valid Kerberos ticket
            try:
                auth = OIDCAuth(role='myapp', use_kerberos=True)
                return HashiCorpVault(url=vault_url, auth_method=auth)
            except:
                pass

        # Fall back to LDAP with PIN+Token
        try:
            def get_pin_token():
                pin = getpass.getpass("PIN: ")
                token = getpass.getpass("Token: ")
                return pin + token

            auth = LDAPAuth(
                username=os.getenv('USER'),
                password_provider=get_pin_token
            )
            return HashiCorpVault(url=vault_url, auth_method=auth)
        except:
            pass

        # Last resort: token from file or environment
        token = os.getenv('VAULT_TOKEN')
        if token:
            auth = TokenAuth(token=token)
            return HashiCorpVault(url=vault_url, auth_method=auth)

        raise Exception("All authentication methods failed")

    vault = get_vault_store()
""")


def example_complete_workflow():
    """Complete example with all components."""
    print("\n" + "="*70)
    print("Example 9: Complete Production Workflow")
    print("="*70)

    print("""
Complete example integrating Vault auth with Config-Stash.

File structure:
    myapp/
    ├── config.yaml
    ├── vault_auth.py
    └── app.py

# vault_auth.py
from config_stash.secret_stores import HashiCorpVault
from config_stash.secret_stores.vault_auth import (
    OIDCAuth, KubernetesAuth, LDAPAuth
)
import os
import getpass

def get_vault_client():
    vault_url = os.getenv('VAULT_ADDR', 'https://vault.example.com')

    # Kubernetes (in cluster)
    if os.path.exists('/var/run/secrets/kubernetes.io/serviceaccount/token'):
        auth = KubernetesAuth(role='myapp')
        return HashiCorpVault(url=vault_url, auth_method=auth)

    # OIDC with Kerberos (developer machine)
    if os.system('klist -s') == 0:
        auth = OIDCAuth(role='myapp-dev', use_kerberos=True)
        return HashiCorpVault(url=vault_url, auth_method=auth)

    # LDAP with PIN+Token (manual login)
    def get_pin_token():
        pin = getpass.getpass("PIN: ")
        token = getpass.getpass("Token: ")
        return pin + token

    auth = LDAPAuth(
        username=os.getenv('USER'),
        password_provider=get_pin_token
    )
    return HashiCorpVault(url=vault_url, auth_method=auth)

# app.py
from config_stash import Config
from config_stash.secret_stores import SecretResolver
from config_stash.loaders import YamlLoader
from vault_auth import get_vault_client

def main():
    # Get Vault client with automatic auth method selection
    vault = get_vault_client()

    # Create config with secret resolution
    config = Config(
        env=os.getenv('ENV', 'production'),
        loaders=[YamlLoader('config.yaml')],
        secret_resolver=SecretResolver(vault),
        enable_ide_support=False
    )

    # Use config with secrets automatically resolved
    db_password = config.database.password  # From Vault
    api_key = config.api.key                # From Vault

    # Your application logic
    connect_to_database(
        host=config.database.host,
        password=db_password
    )

if __name__ == '__main__':
    main()

# config.yaml
production:
  database:
    host: prod-db.example.com
    port: 5432
    username: app_user
    password: "${secret:prod/database/password}"

  api:
    endpoint: https://api.example.com
    key: "${secret:prod/api/key}"
    timeout: 30

development:
  database:
    host: localhost
    port: 5432
    username: dev_user
    password: "${secret:dev/database/password}"

  api:
    endpoint: https://api.dev.example.com
    key: "${secret:dev/api/key}"
    timeout: 60
""")


def main():
    """Run all examples."""
    print("\n" + "="*70)
    print("HashiCorp Vault Authentication Examples")
    print("Advanced Enterprise Authentication Patterns")
    print("="*70)

    example_oidc_with_kerberos()
    example_oidc_browser()
    example_ldap_pin_token()
    example_ldap_kerberos_id()
    example_kubernetes()
    example_aws()
    example_jwt()
    example_multi_auth_fallback()
    example_complete_workflow()

    print("\n" + "="*70)
    print("Summary of Authentication Methods")
    print("="*70)
    print("""
Available Authentication Methods:

1. OIDCAuth - OIDC/OAuth2 with optional Kerberos
   ✓ Kerberos-based (no browser if kinit done)
   ✓ Browser-based flow
   ✓ Custom credential providers

2. LDAPAuth - LDAP with flexible password policies
   ✓ Simple username/password
   ✓ PIN + Token combinations
   ✓ Custom password providers
   ✓ Interactive prompts

3. KerberosAuth - Dedicated Kerberos authentication
   ✓ Uses existing Kerberos ticket
   ✓ No password needed

4. JWTAuth - JWT token authentication
   ✓ External JWT sources
   ✓ CI/CD integration

5. KubernetesAuth - K8s service account
   ✓ Automatic in-cluster auth
   ✓ No configuration needed

6. AWSAuth - AWS IAM/EC2 authentication
   ✓ IAM role based
   ✓ EC2 instance identity

7. AzureAuth - Azure Managed Identity
   ✓ Automatic on Azure VMs/AKS

8. GCPAuth - GCP service account
   ✓ GCE instance identity
   ✓ IAM service account JWT

9. AppRoleAuth - AppRole (CI/CD)
   ✓ Role ID + Secret ID

10. TokenAuth - Direct token (legacy)
   ✓ Pre-existing tokens

All methods support:
- Automatic token renewal where applicable
- Custom mount points
- Namespace support (Vault Enterprise)
- Error handling and fallbacks
""")

    print("\n" + "="*70)
    print("For complete documentation, see:")
    print("docs/SECRET_STORES.md")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
