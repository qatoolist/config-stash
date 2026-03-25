# Config-Stash Development Container

A complete, production-ready development environment for Config-Stash that runs in a Docker container with all necessary tools and services pre-configured.

## 🎯 What's Included

### Development Tools
- **Python 3.12** - Latest stable Python version
- **Git** - Version control with pre-configured aliases
- **GitHub CLI** - GitHub integration from the terminal
- **ZSH with Oh My Zsh** - Enhanced shell experience
- **VS Code Extensions** - Comprehensive extension pack for Python development

### Cloud CLIs
- **AWS CLI v2** - Amazon Web Services command-line interface
- **Azure CLI** - Microsoft Azure command-line interface
- **Google Cloud SDK** - Google Cloud Platform tools
- **HashiCorp Vault CLI** - Vault command-line interface

### Development Services
- **HashiCorp Vault** (port 8200) - Secret management testing
- **LocalStack** (port 4566) - AWS services emulation (S3, Secrets Manager)
- **PostgreSQL** (optional) - Database for integration testing
- **Redis** (optional) - Cache for testing

### Pre-configured Tools
- **Ruff** - Fast Python linter and formatter
- **Black** - Code formatter
- **isort** - Import sorter
- **MyPy** - Static type checker
- **Pytest** - Testing framework with coverage
- **Pre-commit** - Git hooks for code quality

## 🚀 Quick Start

### Prerequisites
- **Docker Desktop** - [Download here](https://www.docker.com/products/docker-desktop)
- **VS Code** - [Download here](https://code.visualstudio.com/)
- **Dev Containers Extension** - Install from VS Code marketplace

### Option 1: VS Code (Recommended)

1. **Open project in VS Code**
   ```bash
   code /path/to/config-stash
   ```

2. **Reopen in Container**
   - Press `F1` or `Cmd/Ctrl+Shift+P`
   - Type: `Dev Containers: Reopen in Container`
   - Wait for container to build (first time takes 5-10 minutes)

3. **Start Coding!**
   - Terminal opens automatically
   - All services are running
   - Extensions are installed
   - Dependencies are ready

### Option 2: Command Line

```bash
# Clone the repository
git clone https://github.com/qatoolist/config-stash.git
cd config-stash

# Open in VS Code Dev Container
code .
# Then use Command Palette: "Reopen in Container"

# Or use devcontainer CLI
devcontainer up --workspace-folder .
devcontainer exec --workspace-folder . bash
```

## 📚 Common Tasks

### Running Tests

```bash
# All tests
make test

# Tests in parallel (faster)
make test-fast

# With coverage report
make test-cov

# Specific test file
pytest tests/test_secret_stores.py

# Using the alias
test
```

### Code Quality

```bash
# Run all checks (lint + type check + format check)
make check

# Lint with Ruff
make lint
# or
lint

# Format code
make format
# or
format

# Type checking
make typecheck
# or
typecheck
```

### Working with Services

#### HashiCorp Vault

```bash
# Check Vault status
vault status

# List secrets
vault kv list secret/

# Get a secret
vault kv get secret/test/database

# Put a secret
vault kv put secret/myapp/db password="secret123"

# Access Vault UI
# Open http://localhost:8200 in browser
# Token: dev-token-12345
```

#### AWS LocalStack

```bash
# List S3 buckets
aws --endpoint-url=http://localhost:4566 s3 ls

# List secrets
aws --endpoint-url=http://localhost:4566 secretsmanager list-secrets

# Get a secret
aws --endpoint-url=http://localhost:4566 secretsmanager get-secret-value \
  --secret-id test/database/password

# Upload config to S3
aws --endpoint-url=http://localhost:4566 s3 cp config.yaml s3://config-stash-test/
```

### Git Workflow

```bash
# Pre-configured aliases
git st          # status
git co          # checkout
git br          # branch
git ci          # commit
git lg          # pretty log graph

# Pre-commit hooks (automatically run on commit)
pre-commit run --all-files
```

## 🏗️ Architecture

### Container Structure

```
┌─────────────────────────────────────────────────────────┐
│ Development Container (app)                             │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │ Python 3.12 + Development Tools                │    │
│  │ - VS Code Extensions                            │    │
│  │ - Ruff, Black, MyPy, Pytest                    │    │
│  │ - AWS/Azure/GCP CLIs                           │    │
│  │ - Vault CLI                                     │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  Mounts:                                                │
│  - Source code → /workspace                            │
│  - SSH keys → ~/.ssh (read-only)                       │
│  - Git config → ~/.gitconfig (read-only)               │
│  - AWS config → ~/.aws (read-only, optional)           │
└─────────────────────────────────────────────────────────┘
           ↓                ↓                ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│    Vault     │  │  LocalStack  │  │  PostgreSQL  │
│   :8200      │  │   :4566      │  │   (optional) │
└──────────────┘  └──────────────┘  └──────────────┘
```

### Service Communication

- **App Container** uses `network_mode: service:vault` to share network with Vault
- All services communicate via `localhost` within the container
- Ports are forwarded to host for browser access
- Services use health checks to ensure proper startup

### Volume Mounts

**Source Code (Cached):**
```
Host: ./
Container: /workspace
```

**Python Caches (Named Volumes for Performance):**
- `pip-cache` → `~/.cache/pip`
- `mypy-cache` → `/workspace/.mypy_cache`
- `pytest-cache` → `/workspace/.pytest_cache`
- `ruff-cache` → `/workspace/.ruff_cache`

**User Configuration (Read-only):**
- SSH keys, Git config, AWS credentials

## ⚙️ Configuration

### Environment Variables

The devcontainer sets up the following environment automatically:

```bash
# Vault
VAULT_ADDR=http://localhost:8200
VAULT_TOKEN=dev-token-12345

# AWS (LocalStack)
AWS_ENDPOINT_URL=http://localhost:4566
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_DEFAULT_REGION=us-east-1

# Python
PYTHONPATH=/workspace
PYTHONDONTWRITEBYTECODE=1
PYTHONUNBUFFERED=1
```

### Customizing Services

Edit `.devcontainer/docker-compose.yml` to:
- Add more services
- Change port mappings
- Modify environment variables
- Adjust resource limits

### Adding VS Code Extensions

Edit `.devcontainer/devcontainer.json`:

```json
"customizations": {
  "vscode": {
    "extensions": [
      "your-extension-id",
      // ... other extensions
    ]
  }
}
```

## 🔧 Troubleshooting

### Container Won't Start

```bash
# Rebuild container without cache
Cmd/Ctrl+Shift+P → "Dev Containers: Rebuild Container Without Cache"

# Or from command line
docker-compose -f .devcontainer/docker-compose.yml build --no-cache
```

### Services Not Ready

```bash
# Check service health
docker-compose -f .devcontainer/docker-compose.yml ps

# View service logs
docker-compose -f .devcontainer/docker-compose.yml logs vault
docker-compose -f .devcontainer/docker-compose.yml logs localstack

# Restart services
docker-compose -f .devcontainer/docker-compose.yml restart vault
```

### Port Already in Use

Edit `.devcontainer/docker-compose.yml` to change port mappings:

```yaml
ports:
  - "8201:8200"  # Use 8201 instead of 8200
```

### Slow Performance on macOS/Windows

The devcontainer uses `:cached` for volume mounts and named volumes for caches to optimize performance. If still slow:

1. Ensure Docker Desktop has enough resources (Settings → Resources)
2. Use named volumes for more paths in `docker-compose.yml`
3. Consider using Docker's built-in performance improvements

### Dependencies Not Found

```bash
# Reinstall dependencies
pip install -r requirements-dev.txt

# Or rebuild container
Cmd/Ctrl+Shift+P → "Dev Containers: Rebuild Container"
```

## 📖 Advanced Usage

### Testing Secret Stores

The devcontainer comes pre-configured with test secrets:

```python
from config_stash import Config
from config_stash.secret_stores import HashiCorpVault, SecretResolver

# Vault secrets (already configured)
vault = HashiCorpVault(
    url='http://localhost:8200',
    token='dev-token-12345'
)
config = Config(secret_resolver=SecretResolver(vault))

# Test secrets available:
# - secret/test/database (password, username)
# - secret/test/api (key, endpoint)
```

### Running Integration Tests

```bash
# All integration tests (uses Vault + LocalStack)
pytest tests/ -v

# Only unit tests (no external services)
pytest tests/ -v -m "not integration"

# Only integration tests
pytest tests/ -v -m integration
```

### Debugging

VS Code debugger is pre-configured. Use F5 to start debugging or:

```json
// .vscode/launch.json is auto-generated
{
  "name": "Python: Current File",
  "type": "python",
  "request": "launch",
  "program": "${file}",
  "console": "integratedTerminal"
}
```

### Performance Optimization

**Cache Named Volumes:**
Already configured for pip, mypy, pytest, and ruff caches.

**Minimal Rebuilds:**
Use `postStartCommand` instead of `postCreateCommand` for scripts that should run on every start.

**Resource Limits:**
Add to services in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
```

## 🎓 Learning Resources

### First Time with Dev Containers?

- [VS Code Dev Containers Tutorial](https://code.visualstudio.com/docs/devcontainers/tutorial)
- [Dev Containers Specification](https://containers.dev/)

### Working with Services

- [HashiCorp Vault Guide](https://developer.hashicorp.com/vault/tutorials)
- [LocalStack Documentation](https://docs.localstack.cloud/)
- [AWS CLI Documentation](https://docs.aws.amazon.com/cli/)

### Config-Stash Specific

- [Secret Stores Guide](../docs/SECRET_STORES.md)
- [Vault Authentication](../docs/VAULT_AUTHENTICATION.md)
- [Main README](../README.md)

## 🤝 Contributing

When contributing, the devcontainer ensures:
- ✅ Consistent development environment
- ✅ All dependencies pre-installed
- ✅ Services configured correctly
- ✅ Pre-commit hooks active
- ✅ Code quality tools ready

Just open in the devcontainer and start coding!

## 📝 Notes

### What Gets Persisted

**✅ Persisted (Named Volumes):**
- Service data (Vault, LocalStack, PostgreSQL)
- Python caches
- Git history

**❌ Not Persisted:**
- Installed packages in container (rebuild to get them)
- Container filesystem changes

### Security

- SSH keys and credentials are mounted read-only
- Dev environment uses test credentials
- Never commit real secrets to the repository
- Vault dev mode is NOT for production

### Performance Tips

- First build takes 5-10 minutes (downloads images, installs dependencies)
- Subsequent starts take ~30 seconds
- Use `make test-fast` for parallel test execution
- Named volumes significantly improve performance

---

**Happy Coding!** 🎉

For issues or questions, check [troubleshooting](#-troubleshooting) or open an issue on GitHub.
