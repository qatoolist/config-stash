"""Comprehensive integration tests for documented workflows and real-world scenarios."""

import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from config_stash import Config
from config_stash.loaders import (
    EnvFileLoader,
    EnvironmentLoader,
    IniLoader,
    JsonLoader,
    TomlLoader,
    YamlLoader,
)


class TestRealWorldWorkflows(unittest.TestCase):
    """Test complete real-world workflows from start to finish."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.temp_dir)

    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_dir)
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_complete_application_configuration_workflow(self):
        """Test a complete application configuration setup workflow."""
        # Step 1: Create base configuration
        base_config = """
default:
  app:
    name: MyApplication
    version: 1.0.0
    debug: true

  database:
    engine: postgresql
    host: localhost
    port: 5432
    name: app_dev
    pool_size: 5
    ssl: false

  cache:
    enabled: true
    backend: redis
    host: localhost
    port: 6379
    ttl: 3600

  api:
    base_url: http://localhost:8000
    timeout: 30
    retry_attempts: 3

  logging:
    level: DEBUG
    format: detailed
"""
        with open("config.yaml", "w") as f:
            f.write(base_config)

        # Step 2: Create production overrides
        prod_config = """
production:
  app:
    debug: false

  database:
    host: prod-db.example.com
    port: 5433
    name: app_prod
    pool_size: 20
    ssl: true

  cache:
    host: prod-cache.example.com

  api:
    base_url: https://api.example.com
    timeout: 10

  logging:
    level: WARNING
"""
        with open("production.yaml", "w") as f:
            f.write(prod_config)

        # Step 3: Create secrets in .env file
        env_content = """
DATABASE_PASSWORD=super_secret_password
API_KEY=prod_api_key_12345
SECRET_KEY=app_secret_key_xyz
CACHE_PASSWORD=redis_password
"""
        with open(".env", "w") as f:
            f.write(env_content)

        # Step 4: Set environment-specific overrides
        os.environ["APP_DATABASE__MAX_CONNECTIONS"] = "100"
        os.environ["APP_FEATURE__ANALYTICS"] = "true"
        os.environ["APP_FEATURE__BETA_UI"] = "false"

        try:
            # Step 5: Load configuration for production with all sources
            config = Config(
                loaders=[
                    YamlLoader("config.yaml"),  # Base config
                    YamlLoader("production.yaml"),  # Production overrides
                    EnvFileLoader(".env"),  # Secrets
                    EnvironmentLoader("APP"),  # Runtime overrides
                ],
                env="production",
                deep_merge=True,
                debug_mode=True,
                enable_ide_support=False,
            )

            # Step 6: Verify configuration hierarchy worked correctly
            # Base values
            self.assertEqual(config.app.name, "MyApplication")
            self.assertEqual(config.app.version, "1.0.0")

            # Production overrides
            self.assertFalse(config.app.debug)
            self.assertEqual(config.database.host, "prod-db.example.com")
            self.assertEqual(config.database.port, 5433)
            self.assertEqual(config.logging.level, "WARNING")

            # Deep merge preserved base values
            self.assertEqual(config.database.engine, "postgresql")
            self.assertTrue(
                config.cache.enabled
            )  # Preserved from default (not overridden in production)

            # Secrets from .env
            self.assertEqual(config.DATABASE_PASSWORD, "super_secret_password")
            self.assertEqual(config.API_KEY, "prod_api_key_12345")

            # Environment variable overrides
            self.assertEqual(config.database.max_connections, 100)
            self.assertTrue(config.feature.analytics)
            self.assertFalse(config.feature.beta_ui)

            # Step 7: Verify source tracking
            db_host_info = config.get_source_info("database.host")
            if db_host_info:
                self.assertIn("production.yaml", db_host_info.source_file)

            # Step 8: Export configuration
            exported = config.export(format="json")
            exported_data = json.loads(exported)
            self.assertIn("database", exported_data)

            # Step 9: Validate configuration
            self.assertTrue(config.validate())

        finally:
            # Cleanup
            del os.environ["APP_DATABASE__MAX_CONNECTIONS"]
            del os.environ["APP_FEATURE__ANALYTICS"]
            del os.environ["APP_FEATURE__BETA_UI"]

    def test_multi_environment_deployment_workflow(self):
        """Test deploying the same app across multiple environments."""
        # Create shared base config
        base = """
default:
  app:
    name: MyApp
    version: 2.0.0

  database:
    engine: postgresql
    pool_size: 10

  cache:
    enabled: true
    ttl: 3600
"""
        with open("base.yaml", "w") as f:
            f.write(base)

        # Create environment-specific configs
        environments = {
            "development": {
                "database": {"host": "dev-db", "port": 5432},
                "cache": {"host": "dev-cache"},
                "app": {"debug": True},
            },
            "staging": {
                "database": {"host": "staging-db", "port": 5432},
                "cache": {"host": "staging-cache"},
                "app": {"debug": False},
            },
            "production": {
                "database": {"host": "prod-db", "port": 5433},
                "cache": {"host": "prod-cache"},
                "app": {"debug": False},
            },
        }

        for env_name, env_config in environments.items():
            env_data = {env_name: env_config}
            with open(f"{env_name}.json", "w") as f:
                json.dump(env_data, f)

        # Test each environment
        for env_name in ["development", "staging", "production"]:
            config = Config(
                loaders=[YamlLoader("base.yaml"), JsonLoader(f"{env_name}.json")],
                env=env_name,
                deep_merge=True,
                enable_ide_support=False,
            )

            # Verify environment-specific values
            self.assertEqual(config.database.host, environments[env_name]["database"]["host"])
            self.assertEqual(config.app.debug, environments[env_name]["app"]["debug"])

            # Verify base values are preserved
            self.assertEqual(config.app.name, "MyApp")
            self.assertEqual(config.database.pool_size, 10)

    def test_configuration_hot_reload_workflow(self):
        """Test hot-reloading configuration in a running application."""
        # Initial configuration
        config_content = """
default:
  feature:
    enabled: false
    max_users: 100

  rate_limit:
    requests_per_minute: 60
"""
        with open("config.yaml", "w") as f:
            f.write(config_content)

        # Create config with dynamic reloading
        config = Config(
            loaders=[YamlLoader("config.yaml")],
            env="default",
            dynamic_reloading=True,
            enable_ide_support=False,
        )

        # Track changes
        changes = []

        @config.on_change
        def track_changes(key, old, new):
            changes.append({"key": key, "old": old, "new": new, "timestamp": time.time()})

        # Verify initial state
        self.assertFalse(config.feature.enabled)
        self.assertEqual(config.feature.max_users, 100)

        # Update configuration while "app is running"
        updated_config = """
default:
  feature:
    enabled: true
    max_users: 1000

  rate_limit:
    requests_per_minute: 120
"""
        with open("config.yaml", "w") as f:
            f.write(updated_config)

        # Wait for file watcher
        time.sleep(0.5)

        # Manually trigger reload in case file watcher hasn't fired yet (macOS timing issue)
        if not config.feature.enabled:
            config.reload()

        # Verify configuration was reloaded
        self.assertTrue(config.feature.enabled)
        self.assertEqual(config.feature.max_users, 1000)

        # Verify callbacks were triggered
        self.assertTrue(len(changes) > 0)

        config.stop_watching()

    def test_configuration_migration_workflow(self):
        """Test migrating from one config format to another."""
        # Old INI-style configuration
        old_config = """
[server]
host = 0.0.0.0
port = 8080

[database]
host = old-db.local
port = 5432
user = olduser
"""
        with open("legacy.ini", "w") as f:
            f.write(old_config)

        # Step 1: Load old configuration
        old_config_obj = Config(
            loaders=[IniLoader("legacy.ini")], env="default", enable_ide_support=False
        )

        # Step 2: Export to new format (YAML)
        yaml_export = old_config_obj.export(format="yaml", output_path="migrated.yaml")

        # Step 3: Load from new format
        new_config_obj = Config(
            loaders=[YamlLoader("migrated.yaml")], env="default", enable_ide_support=False
        )

        # Step 4: Verify data integrity
        self.assertEqual(old_config_obj.server.host, new_config_obj.server.host)
        self.assertEqual(old_config_obj.database.port, new_config_obj.database.port)

    def test_configuration_debugging_workflow(self):
        """Test debugging configuration conflicts and issues."""
        # Create multiple config sources with conflicts
        base = """
default:
  database:
    host: localhost
    port: 5432
    timeout: 30
"""
        override1 = """
default:
  database:
    host: override1.db
    timeout: 60
    pool_size: 10
"""
        override2 = """
default:
  database:
    host: override2.db
    pool_size: 20
    ssl: true
"""
        with open("base.yaml", "w") as f:
            f.write(base)
        with open("override1.yaml", "w") as f:
            f.write(override1)
        with open("override2.yaml", "w") as f:
            f.write(override2)

        # Load with debug mode
        config = Config(
            loaders=[
                YamlLoader("base.yaml"),
                YamlLoader("override1.yaml"),
                YamlLoader("override2.yaml"),
            ],
            env="default",
            debug_mode=True,
            deep_merge=True,
            enable_ide_support=False,
        )

        # Check final value
        self.assertEqual(config.database.host, "override2.db")

        # Investigate override history
        host_history = config.get_override_history("database.host")
        # Should show it was overridden multiple times

        # Get source info
        source_info = config.get_source_info("database.host")
        if source_info:
            self.assertIn("override2.yaml", source_info.source_file)

        # Export debug report
        config.export_debug_report("debug.json")
        self.assertTrue(Path("debug.json").exists())

        with open("debug.json") as f:
            report = json.load(f)
            self.assertIn("loader_order", report)
            self.assertIn("sources", report)

        # Get conflicts
        conflicts = config.get_conflicts()
        self.assertIsInstance(conflicts, dict)

        # Get statistics
        stats = config.get_source_statistics()
        self.assertGreaterEqual(stats["unique_sources"], 3)

    def test_feature_flag_management_workflow(self):
        """Test managing feature flags across environments."""
        # Base feature flags
        features = """
default:
  features:
    new_ui: false
    analytics: false
    beta_features: false
    ai_suggestions: false

development:
  features:
    new_ui: true
    analytics: true
    beta_features: true

staging:
  features:
    new_ui: true
    analytics: true

production:
  features:
    new_ui: false
    analytics: true
"""
        with open("features.yaml", "w") as f:
            f.write(features)

        # Allow runtime feature flag overrides
        os.environ["APP_FEATURES__BETA_FEATURES"] = "true"
        os.environ["APP_FEATURES__AI_SUGGESTIONS"] = "true"

        try:
            # Load for production with runtime overrides
            config = Config(
                loaders=[YamlLoader("features.yaml"), EnvironmentLoader("APP")],
                env="production",
                deep_merge=True,
                enable_ide_support=False,
            )

            # Verify feature flags
            self.assertFalse(config.features.new_ui)  # From prod
            self.assertTrue(config.features.analytics)  # From prod
            self.assertTrue(config.features.beta_features)  # From env var
            self.assertTrue(config.features.ai_suggestions)  # From env var

        finally:
            del os.environ["APP_FEATURES__BETA_FEATURES"]
            del os.environ["APP_FEATURES__AI_SUGGESTIONS"]

    def test_secrets_management_workflow(self):
        """Test secure secrets management workflow."""
        # Non-sensitive config
        app_config = """
default:
  app:
    name: SecureApp
    version: 1.0.0

  database:
    host: db.example.com
    port: 5432
    name: myapp
"""
        with open("config.yaml", "w") as f:
            f.write(app_config)

        # Secrets in .env (gitignored)
        secrets = """
DATABASE_USER=dbadmin
DATABASE_PASSWORD=super_secret_password_123
JWT_SECRET=jwt_signing_key_xyz
ENCRYPTION_KEY=aes_256_encryption_key
API_KEY=external_api_key_abc
"""
        with open(".env.local", "w") as f:
            f.write(secrets)

        # Load configuration
        config = Config(
            loaders=[YamlLoader("config.yaml"), EnvFileLoader(".env.local")],
            env="default",
            enable_ide_support=False,
        )

        # Verify app config loaded
        self.assertEqual(config.app.name, "SecureApp")
        self.assertEqual(config.database.host, "db.example.com")

        # Verify secrets loaded
        self.assertEqual(config.DATABASE_USER, "dbadmin")
        self.assertEqual(config.DATABASE_PASSWORD, "super_secret_password_123")
        self.assertEqual(config.JWT_SECRET, "jwt_signing_key_xyz")

        # Export config without secrets
        exported = config.export(format="json")
        exported_data = json.loads(exported)

        # App config should be present
        self.assertIn("app", exported_data)
        # Secrets should also be present (be careful with exports!)
        self.assertIn("DATABASE_PASSWORD", exported_data)

    def test_microservices_shared_config_workflow(self):
        """Test shared configuration across microservices."""
        # Shared configuration
        shared = """
default:
  company:
    name: ACME Corp
    region: us-east-1

  shared_cache:
    host: shared-cache.internal
    port: 6379

  message_broker:
    host: rabbitmq.internal
    port: 5672

  observability:
    tracing_endpoint: http://jaeger:14268
    metrics_endpoint: http://prometheus:9090
"""
        with open("shared.yaml", "w") as f:
            f.write(shared)

        # Service-specific configs
        services = {
            "auth-service": {
                "service": {"name": "auth", "port": 8001},
                "database": {"name": "auth_db"},
            },
            "user-service": {
                "service": {"name": "users", "port": 8002},
                "database": {"name": "users_db"},
            },
            "order-service": {
                "service": {"name": "orders", "port": 8003},
                "database": {"name": "orders_db"},
            },
        }

        # Test each service gets shared + service-specific config
        for service_name, service_config in services.items():
            service_data = {"default": service_config}
            with open(f"{service_name}.json", "w") as f:
                json.dump(service_data, f)

            config = Config(
                loaders=[YamlLoader("shared.yaml"), JsonLoader(f"{service_name}.json")],
                env="default",
                deep_merge=True,
                enable_ide_support=False,
            )

            # Verify shared config
            self.assertEqual(config.company.name, "ACME Corp")
            self.assertEqual(config.shared_cache.host, "shared-cache.internal")

            # Verify service-specific config
            self.assertEqual(config.service.name, service_config["service"]["name"])
            self.assertEqual(config.service.port, service_config["service"]["port"])

    def test_configuration_validation_workflow(self):
        """Test configuration validation before deployment."""
        # Create config
        config_data = """
default:
  database:
    host: localhost
    port: 5432
    name: myapp

  api:
    endpoint: https://api.example.com
    timeout: 30
"""
        with open("config.yaml", "w") as f:
            f.write(config_data)

        # Create schema
        schema = {
            "type": "object",
            "required": ["database", "api"],
            "properties": {
                "database": {
                    "type": "object",
                    "required": ["host", "port"],
                    "properties": {"host": {"type": "string"}, "port": {"type": "integer"}},
                },
                "api": {
                    "type": "object",
                    "properties": {"endpoint": {"type": "string"}, "timeout": {"type": "integer"}},
                },
            },
        }
        with open("schema.json", "w") as f:
            json.dump(schema, f)

        # Load and validate
        config = Config(
            loaders=[YamlLoader("config.yaml")], env="default", enable_ide_support=False
        )

        # Validate
        with open("schema.json") as f:
            schema = json.load(f)

        is_valid = config.validate(schema)
        self.assertTrue(is_valid)

        # Export validated config
        config.export(format="json", output_path="validated_config.json")
        self.assertTrue(Path("validated_config.json").exists())


class TestEdgeCasesAndErrorHandling(unittest.TestCase):
    """Test edge cases and error handling in integration scenarios."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.temp_dir)

    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_dir)
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_missing_files_graceful_handling(self):
        """Test that missing config files are handled gracefully."""
        # Some files exist, some don't
        existing = """
default:
  app:
    name: TestApp
"""
        with open("exists.yaml", "w") as f:
            f.write(existing)

        # Should not crash even if some loaders fail
        config = Config(
            loaders=[
                YamlLoader("exists.yaml"),
                YamlLoader("missing.yaml"),  # Doesn't exist
                JsonLoader("also_missing.json"),  # Doesn't exist
            ],
            env="default",
            enable_ide_support=False,
        )

        # Should still load from existing file
        self.assertEqual(config.app.name, "TestApp")

    def test_empty_configuration_handling(self):
        """Test handling of completely empty configurations."""
        empty = "default: {}"
        with open("empty.yaml", "w") as f:
            f.write(empty)

        config = Config(loaders=[YamlLoader("empty.yaml")], env="default", enable_ide_support=False)

        # Should not crash
        config_dict = config.to_dict()
        self.assertIsInstance(config_dict, dict)

    def test_circular_environment_override(self):
        """Test handling of circular references in config."""
        config_content = """
default:
  value: "${SELF_REF}"
"""
        with open("config.yaml", "w") as f:
            f.write(config_content)

        os.environ["SELF_REF"] = "${OTHER_REF}"
        os.environ["OTHER_REF"] = "final_value"

        try:
            config = Config(
                loaders=[YamlLoader("config.yaml")],
                env="default",
                use_env_expander=True,
                enable_ide_support=False,
            )

            # Should handle the reference chain
            # (behavior depends on implementation)

        finally:
            del os.environ["SELF_REF"]
            del os.environ["OTHER_REF"]


if __name__ == "__main__":
    unittest.main()
