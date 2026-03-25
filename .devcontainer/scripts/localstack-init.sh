#!/bin/bash
# LocalStack initialization script
# This script runs when LocalStack is ready

set -e

echo "Initializing LocalStack with test resources..."

# AWS CLI endpoint
ENDPOINT="http://localhost:4566"

# Create S3 buckets for testing
echo "Creating S3 buckets..."
aws --endpoint-url=$ENDPOINT s3 mb s3://config-stash-test 2>/dev/null || true
aws --endpoint-url=$ENDPOINT s3 mb s3://config-stash-prod 2>/dev/null || true

# Upload test configuration files to S3
echo "Uploading test config files to S3..."
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

# Create secrets in Secrets Manager
echo "Creating secrets in AWS Secrets Manager..."

# Simple string secrets
aws --endpoint-url=$ENDPOINT secretsmanager create-secret \
    --name test/database/password \
    --secret-string "super-secret-db-password" 2>/dev/null || true

aws --endpoint-url=$ENDPOINT secretsmanager create-secret \
    --name test/api/key \
    --secret-string "api-key-12345" 2>/dev/null || true

# JSON secrets
aws --endpoint-url=$ENDPOINT secretsmanager create-secret \
    --name test/database/config \
    --secret-string '{"host":"localhost","port":5432,"username":"testuser","password":"testpass"}' 2>/dev/null || true

aws --endpoint-url=$ENDPOINT secretsmanager create-secret \
    --name prod/database/password \
    --secret-string "prod-secret-password" 2>/dev/null || true

# Create IAM resources for testing
echo "Creating IAM resources..."
aws --endpoint-url=$ENDPOINT iam create-user --user-name test-user 2>/dev/null || true
aws --endpoint-url=$ENDPOINT iam create-access-key --user-name test-user 2>/dev/null || true

echo "LocalStack initialization complete!"
echo "Available resources:"
echo "  S3 Buckets:"
echo "    - s3://config-stash-test"
echo "    - s3://config-stash-prod"
echo "  Secrets:"
echo "    - test/database/password"
echo "    - test/database/config"
echo "    - test/api/key"
echo "    - prod/database/password"
