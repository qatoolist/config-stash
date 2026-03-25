#!/bin/bash
# Standalone LocalStack setup script
# Run this if LocalStack wasn't configured during initial setup

set -e

echo "Setting up LocalStack..."

# Wait for LocalStack to be ready
echo "Waiting for LocalStack to start..."
max_retries=30
retry_count=0

while [ $retry_count -lt $max_retries ]; do
    if curl -sf http://localhost:4566/_localstack/health >/dev/null 2>&1; then
        echo "✓ LocalStack is ready"
        sleep 2
        break
    fi
    retry_count=$((retry_count + 1))
    echo "  Waiting... ($retry_count/$max_retries)"
    sleep 3
done

if [ $retry_count -eq $max_retries ]; then
    echo "ERROR: LocalStack failed to start"
    exit 1
fi

# AWS endpoint
ENDPOINT="http://localhost:4566"

# Create S3 buckets
echo "Creating S3 buckets..."
aws --endpoint-url=$ENDPOINT s3 mb s3://config-stash-test 2>/dev/null || echo "  Bucket config-stash-test already exists"
aws --endpoint-url=$ENDPOINT s3 mb s3://config-stash-prod 2>/dev/null || echo "  Bucket config-stash-prod already exists"

# Upload test config
echo "Uploading test config to S3..."
cat > /tmp/test-config.yaml << 'EOF'
database:
  host: localhost
  port: 5432
  username: test_user
  password: "${secret:test/database/password}"

api:
  endpoint: https://api.test.com
  key: "${secret:test/api/key}"
  timeout: 30
EOF
aws --endpoint-url=$ENDPOINT s3 cp /tmp/test-config.yaml s3://config-stash-test/config.yaml 2>/dev/null || true

# Create secrets
echo "Creating secrets in AWS Secrets Manager..."
aws --endpoint-url=$ENDPOINT secretsmanager create-secret \
    --name test/database/password \
    --secret-string "super-secret-db-password" 2>/dev/null || echo "  Secret test/database/password already exists"

aws --endpoint-url=$ENDPOINT secretsmanager create-secret \
    --name test/api/key \
    --secret-string "api-key-12345" 2>/dev/null || echo "  Secret test/api/key already exists"

aws --endpoint-url=$ENDPOINT secretsmanager create-secret \
    --name test/database/config \
    --secret-string '{"host":"localhost","port":5432,"username":"testuser","password":"testpass"}' 2>/dev/null || echo "  Secret test/database/config already exists"

aws --endpoint-url=$ENDPOINT secretsmanager create-secret \
    --name prod/database/password \
    --secret-string "prod-secret-password" 2>/dev/null || echo "  Secret prod/database/password already exists"

echo ""
echo "✓ LocalStack setup complete!"
echo ""
echo "Available resources:"
echo "  S3 Buckets:"
echo "    - s3://config-stash-test"
echo "    - s3://config-stash-prod"
echo "  Secrets:"
echo "    - test/database/password"
echo "    - test/database/config"
echo "    - test/api/key"
echo "    - prod/database/password"
echo ""
