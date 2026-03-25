#!/bin/bash
# Post-start script - runs every time the container starts
# Note: This script should never fail to avoid blocking container startup

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🔄 Config-Stash Development Container${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check services (non-blocking)
echo "Checking services..."

# Check Vault
if command -v vault >/dev/null 2>&1 && vault status >/dev/null 2>&1; then
    print_success "HashiCorp Vault is running at http://localhost:8200"
else
    print_info "Vault is starting up (this is normal)"
fi

# Check LocalStack
if curl -sf http://localhost:4566/_localstack/health >/dev/null 2>&1; then
    print_success "LocalStack (AWS) is running at http://localhost:4566"
else
    print_info "LocalStack is starting up (this is normal)"
fi

# Set VAULT_TOKEN if not set
if [ -z "$VAULT_TOKEN" ]; then
    export VAULT_TOKEN="dev-token-12345"
    echo "export VAULT_TOKEN=dev-token-12345" >> ~/.bashrc
    echo "export VAULT_TOKEN=dev-token-12345" >> ~/.zshrc
fi

# Quick environment info
echo ""
echo -e "${BLUE}📊 Environment:${NC}"
if command -v python >/dev/null 2>&1; then
    echo "  Python:     $(python --version 2>&1)"
fi
echo "  Workspace:  $(pwd)"
if git rev-parse --git-dir > /dev/null 2>&1; then
    BRANCH=$(git branch --show-current 2>/dev/null || echo "detached")
    echo "  Git branch: $BRANCH"
fi

echo ""
echo -e "${GREEN}Container is ready!${NC}"
echo ""

# Always exit successfully
exit 0
