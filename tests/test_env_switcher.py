"""Tests for env_switcher and sysenv_fallback features."""

import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

import yaml

from config_stash import Config
from config_stash.loaders import YamlLoader


class TestEnvSwitcher(unittest.TestCase):
    """Test env_switcher parameter — env var controls active environment."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def write_yaml(self, name, data):
        path = os.path.join(self.temp_dir, name)
        with open(path, "w") as f:
            yaml.dump(data, f)
        return path

    def test_env_switcher_reads_from_env_var(self):
        """env_switcher reads the environment name from an env var."""
        path = self.write_yaml("config.yaml", {
            "default": {"host": "localhost"},
            "production": {"host": "prod.db.com"},
        })

        with patch.dict(os.environ, {"APP_ENV": "production"}):
            config = Config(
                env_switcher="APP_ENV",
                loaders=[YamlLoader(path)],
                dynamic_reloading=False,
            )
            self.assertEqual(config.env, "production")
            self.assertEqual(config.host, "prod.db.com")

    def test_env_switcher_falls_back_to_env_param(self):
        """When env var is not set, falls back to env parameter."""
        path = self.write_yaml("config.yaml", {
            "default": {"host": "localhost"},
            "staging": {"host": "staging.db.com"},
        })

        # Remove APP_ENV if it exists
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("APP_ENV", None)
            config = Config(
                env="staging",
                env_switcher="APP_ENV",
                loaders=[YamlLoader(path)],
                dynamic_reloading=False,
            )
            self.assertEqual(config.env, "staging")
            self.assertEqual(config.host, "staging.db.com")

    def test_env_switcher_falls_back_to_default(self):
        """When env var not set and no env param, uses default."""
        path = self.write_yaml("config.yaml", {
            "default": {"host": "localhost"},
            "development": {"host": "dev.db.com"},
        })

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MY_ENV", None)
            config = Config(
                env_switcher="MY_ENV",
                loaders=[YamlLoader(path)],
                dynamic_reloading=False,
            )
            # Falls back to pyproject.toml default_environment
            self.assertIn(config.env, ["development", "default"])

    def test_env_switcher_overrides_env_param(self):
        """env_switcher takes priority over env parameter."""
        path = self.write_yaml("config.yaml", {
            "default": {"host": "localhost"},
            "staging": {"host": "staging.db.com"},
            "production": {"host": "prod.db.com"},
        })

        with patch.dict(os.environ, {"APP_ENV": "production"}):
            config = Config(
                env="staging",  # Would be staging...
                env_switcher="APP_ENV",  # ...but env var says production
                loaders=[YamlLoader(path)],
                dynamic_reloading=False,
            )
            self.assertEqual(config.env, "production")
            self.assertEqual(config.host, "prod.db.com")

    def test_no_env_switcher_uses_env_param(self):
        """Without env_switcher, env param works normally."""
        path = self.write_yaml("config.yaml", {
            "default": {"host": "localhost"},
            "production": {"host": "prod.db.com"},
        })

        config = Config(
            env="production",
            loaders=[YamlLoader(path)],
            dynamic_reloading=False,
        )
        self.assertEqual(config.env, "production")


class TestSysenvFallback(unittest.TestCase):
    """Test sysenv_fallback — auto-fallback to env vars for missing keys."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def write_yaml(self, name, data):
        path = os.path.join(self.temp_dir, name)
        with open(path, "w") as f:
            yaml.dump(data, f)
        return path

    def test_fallback_reads_env_var_for_missing_key(self):
        """Keys not in file config fall back to env vars."""
        path = self.write_yaml("config.yaml", {
            "default": {"host": "localhost"},
        })

        with patch.dict(os.environ, {"DATABASE_PORT": "5432"}):
            config = Config(
                env="default",
                loaders=[YamlLoader(path)],
                sysenv_fallback=True,
                dynamic_reloading=False,
            )

            # From file
            self.assertEqual(config.get("host"), "localhost")
            # From env var fallback (database.port → DATABASE_PORT)
            self.assertEqual(config.get("database.port"), 5432)

    def test_fallback_with_env_prefix(self):
        """With env_prefix, fallback prepends the prefix."""
        path = self.write_yaml("config.yaml", {
            "default": {"host": "from-file"},
        })

        with patch.dict(os.environ, {"MYAPP_DATABASE_PORT": "3306"}):
            config = Config(
                env="default",
                loaders=[YamlLoader(path)],
                env_prefix="MYAPP",
                sysenv_fallback=True,
                dynamic_reloading=False,
            )

            # database.port → MYAPP_DATABASE_PORT
            self.assertEqual(config.get("database.port"), 3306)

    def test_fallback_type_coercion(self):
        """Env var values are type-coerced (int, bool, float)."""
        path = self.write_yaml("config.yaml", {
            "default": {"name": "myapp"},
        })

        with patch.dict(os.environ, {
            "DEBUG": "true",
            "RETRIES": "-3",
            "RATE": "0.75",
        }):
            config = Config(
                env="default",
                loaders=[YamlLoader(path)],
                sysenv_fallback=True,
                dynamic_reloading=False,
            )

            self.assertTrue(config.get("debug"))
            self.assertEqual(config.get("retries"), -3)
            self.assertAlmostEqual(config.get("rate"), 0.75)

    def test_file_config_takes_priority_over_env(self):
        """File config values are NOT overridden by env fallback."""
        path = self.write_yaml("config.yaml", {
            "default": {"host": "from-file"},
        })

        with patch.dict(os.environ, {"HOST": "from-env"}):
            config = Config(
                env="default",
                loaders=[YamlLoader(path)],
                sysenv_fallback=True,
                dynamic_reloading=False,
            )

            # File wins — fallback only kicks in for MISSING keys
            self.assertEqual(config.get("host"), "from-file")

    def test_fallback_returns_default_when_not_in_env_either(self):
        """If key is missing from both file and env, returns default."""
        path = self.write_yaml("config.yaml", {
            "default": {"host": "localhost"},
        })

        config = Config(
            env="default",
            loaders=[YamlLoader(path)],
            sysenv_fallback=True,
            dynamic_reloading=False,
        )

        self.assertEqual(config.get("nonexistent.key", "fallback"), "fallback")

    def test_fallback_disabled_by_default(self):
        """sysenv_fallback=False (default) does not check env vars."""
        path = self.write_yaml("config.yaml", {
            "default": {"host": "localhost"},
        })

        with patch.dict(os.environ, {"DATABASE_PORT": "5432"}):
            config = Config(
                env="default",
                loaders=[YamlLoader(path)],
                sysenv_fallback=False,
                dynamic_reloading=False,
            )

            # Without fallback, missing key returns default
            self.assertIsNone(config.get("database.port"))


if __name__ == "__main__":
    unittest.main()
