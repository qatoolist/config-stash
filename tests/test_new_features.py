"""Tests for newly added features: merge_strategy, env_prefix, freeze, layers."""

import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

import yaml

from config_stash import Config
from config_stash.loaders import YamlLoader


class TestBase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def write_yaml(self, name, data):
        path = os.path.join(self.temp_dir, name)
        with open(path, "w") as f:
            yaml.dump(data, f)
        return path


class TestMergeStrategyIntegration(TestBase):
    """Test that AdvancedConfigMerger is now usable via Config."""

    def test_merge_strategy_replace(self):
        from config_stash.merge_strategies import MergeStrategy

        base = self.write_yaml(
            "base.yaml",
            {
                "default": {
                    "database": {"host": "localhost", "port": 5432},
                    "app": {"name": "myapp", "debug": False},
                }
            },
        )
        override = self.write_yaml(
            "override.yaml",
            {
                "default": {
                    "database": {"host": "production.db"},
                }
            },
        )

        config = Config(
            env="default",
            loaders=[YamlLoader(base), YamlLoader(override)],
            merge_strategy=MergeStrategy.MERGE,
            merge_strategy_map={"default.database": MergeStrategy.REPLACE},
            dynamic_reloading=False,
        )

        # database section should be REPLACED entirely (not deep merged)
        self.assertEqual(config.database.host, "production.db")
        self.assertFalse(
            hasattr(config.database, "port") and config.database.port == 5432
        )

    def test_merge_strategy_default_merge(self):
        from config_stash.merge_strategies import MergeStrategy

        base = self.write_yaml(
            "base.yaml",
            {
                "default": {
                    "database": {"host": "localhost", "port": 5432},
                }
            },
        )
        override = self.write_yaml(
            "override.yaml",
            {
                "default": {
                    "database": {"host": "production.db", "ssl": True},
                }
            },
        )

        config = Config(
            env="default",
            loaders=[YamlLoader(base), YamlLoader(override)],
            merge_strategy=MergeStrategy.MERGE,
            dynamic_reloading=False,
        )

        # Deep merge should preserve port from base
        self.assertEqual(config.database.host, "production.db")
        self.assertEqual(config.database.port, 5432)
        self.assertTrue(config.database.ssl)


class TestEnvPrefix(TestBase):
    """Test env_prefix auto-adds EnvironmentLoader."""

    def test_env_prefix_overrides_file_config(self):
        yaml_path = self.write_yaml(
            "config.yaml",
            {
                "default": {"database": {"host": "localhost", "port": 5432}},
            },
        )

        with patch.dict(os.environ, {"MYAPP_DATABASE__HOST": "from-env"}, clear=False):
            config = Config(
                env="default",
                loaders=[YamlLoader(yaml_path)],
                env_prefix="MYAPP",
                dynamic_reloading=False,
                deep_merge=True,
            )

            # Env var should override file value
            self.assertEqual(config.database.host, "from-env")
            # Non-overridden values preserved
            self.assertEqual(config.database.port, 5432)

    def test_env_prefix_none_does_nothing(self):
        yaml_path = self.write_yaml(
            "config.yaml",
            {
                "default": {"host": "localhost"},
            },
        )

        config = Config(
            env="default",
            loaders=[YamlLoader(yaml_path)],
            env_prefix=None,
            dynamic_reloading=False,
        )

        self.assertEqual(config.host, "localhost")


class TestFreeze(TestBase):
    """Test config.freeze() prevents modifications."""

    def test_freeze_blocks_set(self):
        yaml_path = self.write_yaml(
            "config.yaml",
            {
                "default": {"host": "localhost"},
            },
        )

        config = Config(
            env="default",
            loaders=[YamlLoader(yaml_path)],
            dynamic_reloading=False,
        )

        self.assertFalse(config.is_frozen)

        config.freeze()

        self.assertTrue(config.is_frozen)

        with self.assertRaises(RuntimeError):
            config.set("host", "new-value")

    def test_freeze_blocks_reload(self):
        yaml_path = self.write_yaml(
            "config.yaml",
            {
                "default": {"host": "localhost"},
            },
        )

        config = Config(
            env="default",
            loaders=[YamlLoader(yaml_path)],
            dynamic_reloading=False,
        )

        config.freeze()

        with self.assertRaises(RuntimeError):
            config.reload()

    def test_freeze_does_not_block_reads(self):
        yaml_path = self.write_yaml(
            "config.yaml",
            {
                "default": {"host": "localhost", "port": 5432},
            },
        )

        config = Config(
            env="default",
            loaders=[YamlLoader(yaml_path)],
            dynamic_reloading=False,
        )

        config.freeze()

        # Reads should still work
        self.assertEqual(config.host, "localhost")
        self.assertEqual(config.get("port"), 5432)
        self.assertTrue(config.has("host"))
        _ = config.keys()
        _ = config.to_dict()


class TestLayers(TestBase):
    """Test config.layers property for precedence visibility."""

    def test_layers_shows_all_sources(self):
        yaml_path = self.write_yaml(
            "base.yaml",
            {
                "default": {"host": "localhost", "port": 5432},
            },
        )
        override_path = self.write_yaml(
            "override.yaml",
            {
                "default": {"host": "production"},
            },
        )

        config = Config(
            env="default",
            loaders=[YamlLoader(yaml_path), YamlLoader(override_path)],
            dynamic_reloading=False,
        )

        layers = config.layers

        self.assertEqual(len(layers), 2)
        self.assertIn("base.yaml", layers[0]["source"])
        self.assertIn("override.yaml", layers[1]["source"])
        self.assertEqual(layers[0]["loader_type"], "YamlLoader")

    def test_layers_shows_key_counts(self):
        yaml_path = self.write_yaml(
            "config.yaml",
            {
                "default": {
                    "database": {"host": "localhost", "port": 5432},
                    "app": {"name": "test"},
                },
            },
        )

        config = Config(
            env="default",
            loaders=[YamlLoader(yaml_path)],
            dynamic_reloading=False,
        )

        layers = config.layers
        self.assertEqual(len(layers), 1)
        self.assertGreater(layers[0]["key_count"], 0)


class TestStandaloneValidate(TestBase):
    """Test config.validate() with post-hoc schema."""

    def test_validate_with_pydantic(self):
        try:
            from pydantic import BaseModel
        except ImportError:
            self.skipTest("pydantic not installed")

        class AppConfig(BaseModel):
            host: str
            port: int

        yaml_path = self.write_yaml(
            "config.yaml",
            {
                "default": {"host": "localhost", "port": 5432},
            },
        )

        config = Config(
            env="default",
            loaders=[YamlLoader(yaml_path)],
            dynamic_reloading=False,
        )

        # Validate post-hoc (no schema at init time)
        result = config.validate(schema=AppConfig)
        self.assertTrue(result)

    def test_validate_with_json_schema(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed")

        yaml_path = self.write_yaml(
            "config.yaml",
            {
                "default": {"host": "localhost", "port": 5432},
            },
        )

        config = Config(
            env="default",
            loaders=[YamlLoader(yaml_path)],
            dynamic_reloading=False,
        )

        schema = {
            "type": "object",
            "properties": {
                "host": {"type": "string"},
                "port": {"type": "integer"},
            },
            "required": ["host", "port"],
        }

        result = config.validate(schema=schema)
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
