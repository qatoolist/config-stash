#!/bin/bash
# Post-create script - runs once after container is created
set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Config-Stash Development Container - Post-Create Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print section headers
print_section() {
    echo ""
    echo -e "${BLUE}▶ $1${NC}"
}

# Function to print success messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print info messages
print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# 1. Install Python dependencies
print_section "Installing Python dependencies..."
if [ -f "requirements-dev.txt" ]; then
    pip install --user --no-cache-dir -r requirements-dev.txt
    print_success "Development dependencies installed"
else
    print_info "requirements-dev.txt not found, installing minimal dependencies"
    pip install --user --no-cache-dir -e ".[dev,test,cloud,validation,secrets,all]"
fi

# 2. Install pre-commit hooks
print_section "Setting up pre-commit hooks..."
if [ -f ".pre-commit-config.yaml" ]; then
    pre-commit install
    pre-commit install --hook-type commit-msg
    print_success "Pre-commit hooks installed"
else
    print_info "No .pre-commit-config.yaml found, skipping"
fi

# 3. Setup local git config
print_section "Configuring git..."
git config --global --add safe.directory /workspace
git config --global pull.rebase false
print_success "Git configured"

# 4. Create local development directories
print_section "Creating development directories..."
mkdir -p .pytest_cache
mkdir -p .mypy_cache
mkdir -p .ruff_cache
mkdir -p htmlcov
mkdir -p .coverage
print_success "Development directories created"

# 5. Wait for Vault to be ready and configure it
print_section "Configuring HashiCorp Vault..."
max_retries=30
retry_count=0

while [ $retry_count -lt $max_retries ]; do
    if vault status >/dev/null 2>&1; then
        print_success "Vault is ready"

        # Enable secrets engines
        vault secrets enable -path=secret kv-v2 2>/dev/null || true
        vault secrets enable -path=secret-v1 kv 2>/dev/null || true

        # Create some test secrets
        vault kv put secret/test/database password="test-password" username="test-user" 2>/dev/null || true
        vault kv put secret/test/api key="test-api-key" endpoint="https://api.test.com" 2>/dev/null || true

        print_success "Vault configured with test secrets"
        break
    fi

    retry_count=$((retry_count + 1))
    print_info "Waiting for Vault to be ready... ($retry_count/$max_retries)"
    sleep 2
done

if [ $retry_count -eq $max_retries ]; then
    print_info "Vault not ready yet, you can configure it manually later"
fi

# 6. Wait for LocalStack and configure AWS services
print_section "Configuring AWS LocalStack..."
max_retries=40
retry_count=0

while [ $retry_count -lt $max_retries ]; do
    if curl -sf http://localhost:4566/_localstack/health >/dev/null 2>&1; then
        print_success "LocalStack is ready"
        sleep 2  # Give it a moment to fully initialize

        # Create test S3 buckets
        aws --endpoint-url=http://localhost:4566 s3 mb s3://config-stash-test 2>/dev/null || true
        aws --endpoint-url=http://localhost:4566 s3 mb s3://config-stash-prod 2>/dev/null || true

        # Upload test config file to S3
        cat > /tmp/test-config.yaml << 'EOFCONFIG'
database:
  host: localhost
  port: 5432
  username: test_user
  password: "${secret:test/database/password}"

api:
  endpoint: https://api.test.com
  key: "${secret:test/api/key}"
  timeout: 30
EOFCONFIG
        aws --endpoint-url=http://localhost:4566 s3 cp /tmp/test-config.yaml s3://config-stash-test/config.yaml 2>/dev/null || true

        # Create test secrets in Secrets Manager
        aws --endpoint-url=http://localhost:4566 secretsmanager create-secret \
            --name test/database/password \
            --secret-string "super-secret-db-password" 2>/dev/null || true

        aws --endpoint-url=http://localhost:4566 secretsmanager create-secret \
            --name test/api/key \
            --secret-string "api-key-12345" 2>/dev/null || true

        # Create JSON secret
        aws --endpoint-url=http://localhost:4566 secretsmanager create-secret \
            --name test/database/config \
            --secret-string '{"host":"localhost","port":5432,"username":"testuser","password":"testpass"}' 2>/dev/null || true

        aws --endpoint-url=http://localhost:4566 secretsmanager create-secret \
            --name prod/database/password \
            --secret-string "prod-secret-password" 2>/dev/null || true

        print_success "LocalStack configured with test resources"
        print_info "  S3 buckets: config-stash-test, config-stash-prod"
        print_info "  Secrets: test/database/password, test/api/key, test/database/config"
        break
    fi

    retry_count=$((retry_count + 1))
    print_info "Waiting for LocalStack to be ready... ($retry_count/$max_retries)"
    sleep 3
done

if [ $retry_count -eq $max_retries ]; then
    print_info "LocalStack not ready yet, you can configure it manually later with:"
    print_info "  bash .devcontainer/scripts/setup-localstack.sh"
fi

# 7. Run initial tests to verify setup
print_section "Running initial test verification..."
if python -m pytest tests/ -x -q --tb=line >/dev/null 2>&1; then
    print_success "All tests passed"
else
    print_info "Some tests failed - this is normal on first run. Run 'make test' to see details."
fi

# 8. Display useful information
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✨ Setup Complete!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📚 Quick Start Commands:"
echo "  make test          - Run all tests"
echo "  make test-fast     - Run tests in parallel"
echo "  make lint          - Run linters"
echo "  make format        - Format code"
echo "  make check         - Run all checks"
echo ""
echo "🔧 Service URLs:"
echo "  HashiCorp Vault:   http://localhost:8200"
echo "  LocalStack:        http://localhost:4566"
echo "  Vault Token:       dev-token-12345"
echo ""
echo "💡 Useful Aliases:"
echo "  test               - pytest tests/"
echo "  test-cov           - pytest with coverage"
echo "  lint               - ruff check ."
echo "  format             - black . && isort ."
echo "  typecheck          - mypy src/config_stash"
echo ""
echo "📖 Documentation:"
echo "  README.md                        - Project overview"
echo "  docs/SECRET_STORES.md            - Secret store guide"
echo "  docs/VAULT_AUTHENTICATION.md     - Vault auth guide"
echo "  .devcontainer/README.md          - Devcontainer docs"
echo ""
echo -e "${BLUE}Happy coding! 🎉${NC}"
echo ""
