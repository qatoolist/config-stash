"""Comprehensive tests for secret store integration."""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from config_stash import Config
from config_stash.loaders import YamlLoader
from config_stash.secret_stores import (
    DictSecretStore,
    EnvSecretStore,
    MultiSecretStore,
    SecretResolver,
)
from config_stash.secret_stores.base import (
    SecretAccessError,
    SecretNotFoundError,
    SecretStoreError,
)


class TestDictSecretStore(unittest.TestCase):
    """Test the in-memory dict-based secret store."""

    def test_basic_get_set(self):
        """Test basic get and set operations."""
        store = DictSecretStore()
        store.set_secret("test/key", "test-value")

        result = store.get_secret("test/key")
        self.assertEqual(result, "test-value")

    def test_get_nonexistent_secret(self):
        """Test getting a non-existent secret raises error."""
        store = DictSecretStore()

        with self.assertRaises(SecretNotFoundError):
            store.get_secret("nonexistent/key")

    def test_dict_value_storage(self):
        """Test storing and retrieving dict values."""
        store = DictSecretStore()
        config_dict = {"host": "localhost", "port": 5432, "password": "secret"}

        store.set_secret("db/config", config_dict)
        result = store.get_secret("db/config")

        self.assertEqual(result, config_dict)
        self.assertEqual(result["host"], "localhost")

    def test_delete_secret(self):
        """Test deleting a secret."""
        store = DictSecretStore({"api/key": "abc123"})

        self.assertTrue(store.secret_exists("api/key"))
        store.delete_secret("api/key")
        self.assertFalse(store.secret_exists("api/key"))

    def test_list_secrets(self):
        """Test listing all secrets."""
        store = DictSecretStore(
            {
                "api/key": "value1",
                "db/password": "value2",
                "redis/url": "value3",
            }
        )

        all_secrets = store.list_secrets()
        self.assertEqual(len(all_secrets), 3)
        self.assertIn("api/key", all_secrets)

    def test_list_with_prefix(self):
        """Test listing secrets with prefix filter."""
        store = DictSecretStore(
            {
                "prod/api/key": "value1",
                "prod/db/password": "value2",
                "dev/api/key": "value3",
            }
        )

        prod_secrets = store.list_secrets(prefix="prod/")
        self.assertEqual(len(prod_secrets), 2)
        self.assertTrue(all(s.startswith("prod/") for s in prod_secrets))

    def test_secret_versioning(self):
        """Test secret versioning functionality."""
        store = DictSecretStore()

        store.set_secret("api/key", "v1", keep_versions=True)
        store.set_secret("api/key", "v2", keep_versions=True)
        store.set_secret("api/key", "v3", keep_versions=True)

        # Get latest
        latest = store.get_secret("api/key")
        self.assertEqual(latest, "v3")

        # Get specific versions
        v1 = store.get_secret("api/key", version="0")
        self.assertEqual(v1, "v1")

        v2 = store.get_secret("api/key", version="1")
        self.assertEqual(v2, "v2")

    def test_metadata(self):
        """Test secret metadata retrieval."""
        store = DictSecretStore({"api/key": "abc123"})

        metadata = store.get_secret_metadata("api/key")
        self.assertEqual(metadata["key"], "api/key")
        self.assertEqual(metadata["type"], "str")

    def test_clear(self):
        """Test clearing all secrets."""
        store = DictSecretStore({"key1": "value1", "key2": "value2"})

        self.assertEqual(len(store), 2)
        store.clear()
        self.assertEqual(len(store), 0)

    def test_update_bulk(self):
        """Test bulk updating secrets."""
        store = DictSecretStore()
        secrets = {
            "api/key": "abc123",
            "db/password": "secret",
            "redis/url": "redis://localhost",
        }

        store.update(secrets)
        self.assertEqual(len(store), 3)
        self.assertEqual(store.get_secret("api/key"), "abc123")


class TestEnvSecretStore(unittest.TestCase):
    """Test the environment variable-based secret store."""

    def setUp(self):
        """Set up test environment variables."""
        self.original_env = os.environ.copy()

    def tearDown(self):
        """Restore original environment."""
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_get_secret_with_transformation(self):
        """Test getting secret with key transformation."""
        os.environ["API_KEY"] = "test-key-123"

        store = EnvSecretStore(transform_key=True)
        result = store.get_secret("api/key")

        self.assertEqual(result, "test-key-123")

    def test_get_secret_without_transformation(self):
        """Test getting secret without key transformation."""
        os.environ["my_exact_var"] = "value"

        store = EnvSecretStore(transform_key=False)
        result = store.get_secret("my_exact_var")

        self.assertEqual(result, "value")

    def test_set_secret(self):
        """Test setting environment variable."""
        store = EnvSecretStore(transform_key=True)
        store.set_secret("test/secret", "new-value")

        self.assertEqual(os.environ["TEST_SECRET"], "new-value")

    def test_prefix_and_suffix(self):
        """Test prefix and suffix functionality."""
        os.environ["SECRET_API_KEY_PROD"] = "value"

        store = EnvSecretStore(prefix="SECRET_", suffix="_PROD", transform_key=True)
        result = store.get_secret("api/key")

        self.assertEqual(result, "value")

    def test_list_secrets(self):
        """Test listing environment variables."""
        os.environ["SECRET_KEY1"] = "value1"
        os.environ["SECRET_KEY2"] = "value2"
        os.environ["OTHER_VAR"] = "value3"

        store = EnvSecretStore(prefix="SECRET_", transform_key=False)
        secrets = store.list_secrets()

        self.assertGreaterEqual(len(secrets), 2)
        self.assertIn("SECRET_KEY1", secrets)
        self.assertIn("SECRET_KEY2", secrets)

    def test_delete_secret(self):
        """Test deleting environment variable."""
        os.environ["TEST_VAR"] = "value"
        store = EnvSecretStore(transform_key=False)

        store.delete_secret("TEST_VAR")
        self.assertNotIn("TEST_VAR", os.environ)


class TestMultiSecretStore(unittest.TestCase):
    """Test the multi-store composite functionality."""

    def test_fallback_resolution(self):
        """Test fallback resolution across multiple stores."""
        primary = DictSecretStore({"api/key": "primary-value"})
        fallback = DictSecretStore({"db/password": "fallback-value"})

        multi = MultiSecretStore([primary, fallback])

        # Should get from primary
        self.assertEqual(multi.get_secret("api/key"), "primary-value")

        # Should fallback to second store
        self.assertEqual(multi.get_secret("db/password"), "fallback-value")

    def test_primary_override(self):
        """Test that primary store overrides fallback."""
        primary = DictSecretStore({"api/key": "primary-value"})
        fallback = DictSecretStore({"api/key": "fallback-value"})

        multi = MultiSecretStore([primary, fallback])

        # Should get from primary, not fallback
        self.assertEqual(multi.get_secret("api/key"), "primary-value")

    def test_secret_not_found_in_any_store(self):
        """Test error when secret not found in any store."""
        store1 = DictSecretStore({"key1": "value1"})
        store2 = DictSecretStore({"key2": "value2"})

        multi = MultiSecretStore([store1, store2])

        with self.assertRaises(SecretNotFoundError):
            multi.get_secret("nonexistent")

    def test_list_unique_secrets(self):
        """Test listing unique secrets across all stores."""
        store1 = DictSecretStore({"api/key": "v1", "db/password": "v1"})
        store2 = DictSecretStore({"api/key": "v2", "redis/url": "v2"})

        multi = MultiSecretStore([store1, store2])
        secrets = multi.list_secrets()

        # Should have unique set of keys
        self.assertEqual(len(secrets), 3)
        self.assertIn("api/key", secrets)
        self.assertIn("db/password", secrets)
        self.assertIn("redis/url", secrets)

    def test_write_to_first(self):
        """Test that writes go to first store only."""
        store1 = DictSecretStore()
        store2 = DictSecretStore()

        multi = MultiSecretStore([store1, store2], write_to_first=True)
        multi.set_secret("new/key", "value")

        # Should only be in first store
        self.assertTrue(store1.secret_exists("new/key"))
        self.assertFalse(store2.secret_exists("new/key"))

    def test_get_store_for_secret(self):
        """Test finding which store contains a secret."""
        store1 = DictSecretStore({"key1": "value1"})
        store2 = DictSecretStore({"key2": "value2"})

        multi = MultiSecretStore([store1, store2])

        source = multi.get_store_for_secret("key2")
        self.assertEqual(source, store2)


class TestSecretResolver(unittest.TestCase):
    """Test the secret resolver integration."""

    def test_simple_placeholder_resolution(self):
        """Test resolving a simple secret placeholder."""
        store = DictSecretStore({"db/password": "super-secret"})
        resolver = SecretResolver(store)

        result = resolver.resolve("${secret:db/password}")
        self.assertEqual(result, "super-secret")

    def test_placeholder_in_string(self):
        """Test placeholder within a larger string."""
        store = DictSecretStore({"db/password": "secret123"})
        resolver = SecretResolver(store)

        result = resolver.resolve(
            "postgresql://user:${secret:db/password}@localhost/db"
        )
        self.assertEqual(result, "postgresql://user:secret123@localhost/db")

    def test_multiple_placeholders(self):
        """Test multiple placeholders in one string."""
        store = DictSecretStore(
            {
                "db/user": "admin",
                "db/password": "secret123",
            }
        )
        resolver = SecretResolver(store)

        result = resolver.resolve(
            "User: ${secret:db/user}, Pass: ${secret:db/password}"
        )
        self.assertEqual(result, "User: admin, Pass: secret123")

    def test_json_path_extraction(self):
        """Test extracting nested value from JSON secret."""
        store = DictSecretStore(
            {
                "db/config": {
                    "host": "localhost",
                    "port": 5432,
                    "credentials": {"user": "admin", "password": "secret"},
                }
            }
        )
        resolver = SecretResolver(store)

        # Extract nested value
        result = resolver.resolve("${secret:db/config:credentials.password}")
        self.assertEqual(result, "secret")

    def test_caching(self):
        """Test that resolved secrets are cached."""
        store = DictSecretStore({"api/key": "abc123"})
        resolver = SecretResolver(store, cache_enabled=True)

        # Resolve once
        result1 = resolver.resolve("${secret:api/key}")

        # Change the underlying store
        store.set_secret("api/key", "new-value")

        # Should still get cached value
        result2 = resolver.resolve("${secret:api/key}")

        self.assertEqual(result1, result2)
        self.assertEqual(result2, "abc123")

    def test_cache_clear(self):
        """Test clearing the cache."""
        store = DictSecretStore({"api/key": "abc123"})
        resolver = SecretResolver(store, cache_enabled=True)

        # Resolve and cache
        resolver.resolve("${secret:api/key}")

        # Change store and clear cache
        store.set_secret("api/key", "new-value")
        resolver.clear_cache()

        # Should get new value
        result = resolver.resolve("${secret:api/key}")
        self.assertEqual(result, "new-value")

    def test_fail_on_missing_true(self):
        """Test that missing secrets raise error when fail_on_missing=True."""
        store = DictSecretStore()
        resolver = SecretResolver(store, fail_on_missing=True)

        with self.assertRaises(SecretNotFoundError):
            resolver.resolve("${secret:nonexistent}")

    def test_fail_on_missing_false(self):
        """Test that missing secrets are left unchanged when fail_on_missing=False."""
        store = DictSecretStore()
        resolver = SecretResolver(store, fail_on_missing=False)

        result = resolver.resolve("${secret:nonexistent}")
        self.assertEqual(result, "${secret:nonexistent}")

    def test_prefix(self):
        """Test resolver with prefix."""
        store = DictSecretStore({"prod/api/key": "abc123"})
        resolver = SecretResolver(store, prefix="prod/")

        # Should automatically prepend prefix
        result = resolver.resolve("${secret:api/key}")
        self.assertEqual(result, "abc123")

    def test_non_string_values_unchanged(self):
        """Test that non-string values are not processed."""
        store = DictSecretStore({"key": "value"})
        resolver = SecretResolver(store)

        # These should be returned unchanged
        self.assertEqual(resolver.resolve(123), 123)
        self.assertEqual(resolver.resolve(True), True)
        self.assertEqual(resolver.resolve(None), None)

    def test_prefetch_secrets(self):
        """Test prefetching secrets into cache."""
        store = DictSecretStore(
            {
                "api/key": "abc123",
                "db/password": "secret",
            }
        )
        resolver = SecretResolver(store, cache_enabled=True)

        resolver.prefetch_secrets(["api/key", "db/password"])

        # Cache should have both
        stats = resolver.cache_stats
        self.assertEqual(stats["size"], 2)


class TestConfigIntegration(unittest.TestCase):
    """Test secret resolver integration with Config class."""

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

    def test_config_with_secret_resolver(self):
        """Test Config class with secret resolver."""
        # Create config file with secret placeholders
        config_content = """
default:
  database:
    host: localhost
    password: "${secret:db/password}"
  api:
    key: "${secret:api/key}"
"""
        with open("config.yaml", "w") as f:
            f.write(config_content)

        # Create secret store
        secrets = DictSecretStore(
            {
                "db/password": "super-secret-password",
                "api/key": "abc123xyz789",
            }
        )

        # Create config with secret resolver
        config = Config(
            env="default",
            loaders=[YamlLoader("config.yaml")],
            secret_resolver=SecretResolver(secrets),
            enable_ide_support=False,
        )

        # Secrets should be resolved
        self.assertEqual(config.database.password, "super-secret-password")
        self.assertEqual(config.api.key, "abc123xyz789")

    def test_config_without_secret_resolver(self):
        """Test that placeholders remain unchanged without resolver."""
        config_content = """
default:
  api:
    key: "${secret:api/key}"
"""
        with open("config.yaml", "w") as f:
            f.write(config_content)

        # Config without secret resolver
        config = Config(
            env="default",
            loaders=[YamlLoader("config.yaml")],
            secret_resolver=None,
            enable_ide_support=False,
        )

        # Placeholder should remain unchanged
        self.assertEqual(config.api.key, "${secret:api/key}")

    def test_secret_resolver_with_multi_store(self):
        """Test using multi-store with Config."""
        config_content = """
default:
  database:
    password: "${secret:db/password}"
  api:
    key: "${secret:api/key}"
"""
        with open("config.yaml", "w") as f:
            f.write(config_content)

        # Create multi-store with fallback
        primary = DictSecretStore({"db/password": "from-primary"})
        fallback = DictSecretStore({"api/key": "from-fallback"})
        multi_store = MultiSecretStore([primary, fallback])

        # Create config
        config = Config(
            env="default",
            loaders=[YamlLoader("config.yaml")],
            secret_resolver=SecretResolver(multi_store),
            enable_ide_support=False,
        )

        # Should resolve from appropriate stores
        self.assertEqual(config.database.password, "from-primary")
        self.assertEqual(config.api.key, "from-fallback")


if __name__ == "__main__":
    unittest.main()
