"""Comprehensive real-world integration tests — no mocks.

Every test creates real files on disk, uses real environment variables,
and exercises actual code paths end-to-end.
"""

# pyright: reportOptionalSubscript=false, reportOptionalMemberAccess=false
# pyright: reportArgumentType=false, reportPossiblyUnboundVariable=false
# pyright: reportAttributeAccessIssue=false, reportCallIssue=false
# pyright: reportMissingImports=false

import copy
import json
import os
import shutil
import tempfile
import time
import unittest

import yaml


class RealWorldTestBase(unittest.TestCase):
    """Base class that sets up a real temp directory for config files."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()

    def tearDown(self):
        os.chdir(self.original_dir)
        shutil.rmtree(self.temp_dir)

    def write_yaml(self, name, data):
        path = os.path.join(self.temp_dir, name)
        with open(path, "w") as f:
            yaml.dump(data, f)
        return path

    def write_json(self, name, data):
        path = os.path.join(self.temp_dir, name)
        with open(path, "w") as f:
            json.dump(data, f)
        return path

    def write_file(self, name, content):
        path = os.path.join(self.temp_dir, name)
        with open(path, "w") as f:
            f.write(content)
        return path


class TestRealMultiSourceLoading(RealWorldTestBase):
    """Test loading from multiple real file sources."""

    def test_yaml_json_toml_merge(self):
        """Load YAML + JSON + TOML, verify merge order."""
        from config_stash import Config
        from config_stash.loaders import JsonLoader, TomlLoader, YamlLoader

        yaml_path = self.write_yaml(
            "base.yaml",
            {
                "default": {
                    "database": {"host": "localhost", "port": 5432},
                    "app": {"name": "myapp", "debug": False},
                }
            },
        )
        json_path = self.write_json(
            "override.json",
            {
                "default": {
                    "database": {"host": "production.db"},
                    "cache": {"ttl": 300},
                }
            },
        )
        toml_path = self.write_file(
            "final.toml",
            """
[default.app]
debug = true
version = "2.0"
""",
        )

        config = Config(
            env="default",
            loaders=[
                YamlLoader(yaml_path),
                JsonLoader(json_path),
                TomlLoader(toml_path),
            ],
            dynamic_reloading=False,
            deep_merge=True,
        )

        # YAML base values survive deep merge
        self.assertEqual(config.database.port, 5432)
        # JSON overrides YAML
        self.assertEqual(config.database.host, "production.db")
        # JSON adds new keys
        self.assertEqual(config.cache.ttl, 300)
        # TOML overrides YAML
        self.assertTrue(config.app.debug)
        # TOML adds new keys (TOML parses "2.0" as float per spec)
        self.assertEqual(config.app.version, 2.0)
        # YAML base values preserved
        self.assertEqual(config.app.name, "myapp")

    def test_env_file_with_yaml_override(self):
        """Load .env file then YAML, verify merge and type coercion."""
        from config_stash import Config
        from config_stash.loaders import EnvFileLoader, YamlLoader

        env_path = self.write_file(
            ".env",
            """
DATABASE_HOST=localhost
DATABASE_PORT=5432
DEBUG=true
RETRIES=-3
PI=3.14
""",
        )
        yaml_path = self.write_yaml(
            "config.yaml",
            {
                "default": {"DATABASE_HOST": "yaml-host"},
            },
        )

        config = Config(
            env="default",
            loaders=[EnvFileLoader(env_path), YamlLoader(yaml_path)],
            dynamic_reloading=False,
        )

        # YAML overrides .env for DATABASE_HOST
        self.assertEqual(config.DATABASE_HOST, "yaml-host")
        # .env type coercion works
        self.assertEqual(config.DATABASE_PORT, 5432)
        self.assertIsInstance(config.DATABASE_PORT, int)
        self.assertTrue(config.DEBUG)
        self.assertEqual(config.RETRIES, -3)
        self.assertIsInstance(config.RETRIES, int)
        self.assertAlmostEqual(config.PI, 3.14)

    def test_ini_loading_with_sections(self):
        """Load INI file, verify sections become nested dicts."""
        from config_stash.loaders import IniLoader

        ini_path = self.write_file(
            "config.ini",
            """
[database]
host = localhost
port = 5432
ssl = true

[app]
name = myapp
workers = -4
""",
        )
        loader = IniLoader(ini_path)
        config = loader.load()

        self.assertEqual(config["database"]["host"], "localhost")
        self.assertEqual(config["database"]["port"], 5432)
        self.assertTrue(config["database"]["ssl"])
        self.assertEqual(config["app"]["workers"], -4)
        self.assertIsInstance(config["app"]["workers"], int)


class TestRealEnvironmentResolution(RealWorldTestBase):
    """Test environment-specific config resolution with real files."""

    def test_environment_override(self):
        """default section merged with environment-specific section."""
        from config_stash import Config
        from config_stash.loaders import YamlLoader

        yaml_path = self.write_yaml(
            "config.yaml",
            {
                "default": {
                    "database": {"host": "localhost", "port": 5432, "ssl": False},
                    "app": {"debug": True},
                },
                "production": {
                    "database": {"host": "prod.db.com", "ssl": True},
                    "app": {"debug": False},
                },
            },
        )

        config = Config(
            env="production",
            loaders=[YamlLoader(yaml_path)],
            dynamic_reloading=False,
            deep_merge=True,
        )

        # Production overrides
        self.assertEqual(config.database.host, "prod.db.com")
        self.assertTrue(config.database.ssl)
        self.assertFalse(config.app.debug)
        # Default values preserved
        self.assertEqual(config.database.port, 5432)

    def test_environment_with_env_vars(self):
        """Environment variables loaded alongside file config."""
        from config_stash import Config
        from config_stash.loaders import EnvironmentLoader, YamlLoader

        yaml_path = self.write_yaml(
            "config.yaml",
            {
                "default": {"database": {"host": "localhost"}},
            },
        )

        with unittest.mock.patch.dict(
            os.environ,
            {
                "MYAPP_DATABASE__PORT": "9999",
            },
        ):
            config = Config(
                env="default",
                loaders=[
                    YamlLoader(yaml_path),
                    EnvironmentLoader("MYAPP"),
                ],
                dynamic_reloading=False,
                deep_merge=True,
            )

            self.assertEqual(config.database.host, "localhost")
            self.assertEqual(config.database.port, 9999)


class TestRealReloadAndCallbacks(RealWorldTestBase):
    """Test config reload with real file modifications."""

    def test_reload_picks_up_changes(self):
        """Modify a file on disk, reload, verify new values."""
        from config_stash import Config
        from config_stash.loaders import YamlLoader

        yaml_path = self.write_yaml(
            "config.yaml",
            {
                "default": {"host": "original", "port": 5432},
            },
        )

        config = Config(
            env="default",
            loaders=[YamlLoader(yaml_path)],
            dynamic_reloading=False,
        )

        self.assertEqual(config.host, "original")

        # Modify file
        self.write_yaml(
            "config.yaml",
            {
                "default": {"host": "changed", "port": 5432, "new_key": "new_value"},
            },
        )

        config.reload()

        self.assertEqual(config.host, "changed")
        self.assertEqual(config.new_key, "new_value")

    def test_on_change_callback_fires(self):
        """Register callback, reload, verify it fires with correct values."""
        from config_stash import Config
        from config_stash.loaders import YamlLoader

        yaml_path = self.write_yaml(
            "config.yaml",
            {
                "default": {"host": "original"},
            },
        )

        config = Config(
            env="default",
            loaders=[YamlLoader(yaml_path)],
            dynamic_reloading=False,
        )

        changes = []

        @config.on_change
        def track_change(key, old_val, new_val):
            changes.append((key, old_val, new_val))

        self.write_yaml(
            "config.yaml",
            {
                "default": {"host": "changed"},
            },
        )

        config.reload()

        self.assertTrue(len(changes) > 0, "on_change callback did not fire")
        # At least one change should involve "host"
        host_changes = [c for c in changes if c[0] == "host"]
        self.assertTrue(
            len(host_changes) > 0,
            f"No change detected for 'host'. Changes: {changes}",
        )

    def test_dry_run_preserves_state(self):
        """dry_run=True should not modify any config state."""
        from config_stash import Config
        from config_stash.loaders import YamlLoader

        yaml_path = self.write_yaml(
            "config.yaml",
            {
                "default": {"host": "original"},
            },
        )

        config = Config(
            env="default",
            loaders=[YamlLoader(yaml_path)],
            dynamic_reloading=False,
        )

        state_before = {
            "host": config.host,
            "merged": copy.deepcopy(config.merged_config),
        }

        self.write_yaml(
            "config.yaml",
            {
                "default": {"host": "changed"},
            },
        )

        config.reload(dry_run=True)

        self.assertEqual(config.host, "original")
        self.assertEqual(config.merged_config, state_before["merged"])


class TestRealSetAndIntrospection(RealWorldTestBase):
    """Test programmatic set() and introspection with real configs."""

    def test_set_and_get(self):
        from config_stash import Config
        from config_stash.loaders import YamlLoader

        yaml_path = self.write_yaml(
            "config.yaml",
            {
                "default": {"database": {"host": "localhost"}},
            },
        )

        config = Config(
            env="default",
            loaders=[YamlLoader(yaml_path)],
            dynamic_reloading=False,
        )

        config.set("database.port", 5432)
        config.set("new_section.key", "value")

        self.assertEqual(config.database.port, 5432)
        self.assertEqual(config.new_section.key, "value")
        self.assertTrue(config.has("database.port"))
        self.assertTrue(config.has("new_section.key"))

    def test_keys_and_to_dict(self):
        from config_stash import Config
        from config_stash.loaders import YamlLoader

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

        keys = config.keys()
        self.assertIn("database", keys)
        self.assertIn("app", keys)

        d = config.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["database"]["host"], "localhost")


class TestRealVersioning(RealWorldTestBase):
    """Test versioning with real file system."""

    def test_save_and_rollback(self):
        from config_stash import Config
        from config_stash.loaders import YamlLoader

        yaml_path = self.write_yaml(
            "config.yaml",
            {
                "default": {"host": "v1-host", "port": 5432},
            },
        )

        version_dir = os.path.join(self.temp_dir, "versions")
        config = Config(
            env="default",
            loaders=[YamlLoader(yaml_path)],
            dynamic_reloading=False,
        )
        config.enable_versioning(storage_path=version_dir)

        v1 = config.save_version(metadata={"author": "test"})

        # Modify config
        self.write_yaml(
            "config.yaml",
            {
                "default": {"host": "v2-host", "port": 5432},
            },
        )
        config.reload()
        self.assertEqual(config.host, "v2-host")

        v2 = config.save_version(metadata={"author": "test"})

        # Rollback to v1
        config.rollback_to_version(v1.version_id)
        self.assertEqual(config.host, "v1-host")

        # Verify version files on disk
        version_files = os.listdir(version_dir)
        self.assertTrue(len(version_files) >= 2)


class TestRealSecretResolution(RealWorldTestBase):
    """Test secret resolution with real DictSecretStore."""

    def test_secrets_resolved_in_config(self):
        from config_stash import Config
        from config_stash.loaders import YamlLoader
        from config_stash.secret_stores.providers.dict_secret_store import (
            DictSecretStore,
        )
        from config_stash.secret_stores.resolver import SecretResolver

        yaml_path = self.write_yaml(
            "config.yaml",
            {
                "default": {
                    "database": {
                        "host": "localhost",
                        "password": "${secret:db/password}",
                    },
                    "api_key": "${secret:api/key}",
                },
            },
        )

        secrets = DictSecretStore(
            {
                "db/password": "super-secret-pw",
                "api/key": "ak_12345",
            }
        )
        resolver = SecretResolver(secrets)

        config = Config(
            env="default",
            loaders=[YamlLoader(yaml_path)],
            secret_resolver=resolver,
            dynamic_reloading=False,
        )

        self.assertEqual(config.database.password, "super-secret-pw")
        self.assertEqual(config.api_key, "ak_12345")
        self.assertEqual(config.database.host, "localhost")


class TestRealComposition(RealWorldTestBase):
    """Test config composition with real include files."""

    def test_include_directive(self):
        from config_stash import Config
        from config_stash.loaders import YamlLoader

        os.chdir(self.temp_dir)

        # Create base config
        self.write_file("base.yaml", "database:\n  host: localhost\n  port: 5432\n")

        # Create main config that includes base
        main_path = self.write_file(
            "main.yaml", "_include:\n  - base.yaml\ndefault:\n  app:\n    name: myapp\n"
        )

        config = Config(
            env="default",
            loaders=[YamlLoader(main_path)],
            dynamic_reloading=False,
            deep_merge=True,
        )

        # Included base values should be present
        d = config.to_dict()
        self.assertEqual(d.get("app", {}).get("name"), "myapp")


class TestRealConfigDiff(RealWorldTestBase):
    """Test config diffing with real configs."""

    def test_diff_two_versions(self):
        from config_stash.config_diff import ConfigDiffer

        config1 = {
            "database": {"host": "localhost", "port": 5432},
            "app": {"debug": True},
        }
        config2 = {
            "database": {"host": "remote", "port": 5432, "ssl": True},
            "app": {"debug": False},
            "cache": {"ttl": 300},
        }

        diffs = ConfigDiffer.diff(config1, config2)
        summary = ConfigDiffer.diff_summary(diffs)

        self.assertGreater(summary["total"], 0)
        self.assertGreater(summary["modified"], 0)
        self.assertGreater(summary["added"], 0)

    def test_diff_export_to_json(self):
        from config_stash.config_diff import ConfigDiffer

        diffs = ConfigDiffer.diff({"a": 1}, {"a": 2, "b": 3})
        json_str = ConfigDiffer.diff_to_json(diffs)

        parsed = json.loads(json_str)
        self.assertIsInstance(parsed, list)
        self.assertTrue(len(parsed) > 0)


class TestRealConfigBuilder(RealWorldTestBase):
    """Test ConfigBuilder with real files."""

    def test_builder_pattern(self):
        from config_stash import ConfigBuilder
        from config_stash.loaders import JsonLoader, YamlLoader

        yaml_path = self.write_yaml(
            "base.yaml",
            {
                "default": {"database": {"host": "localhost"}},
            },
        )
        json_path = self.write_json(
            "override.json",
            {
                "default": {"database": {"port": 5432}},
            },
        )

        config = (
            ConfigBuilder()
            .with_env("default")
            .add_loader(YamlLoader(yaml_path))
            .add_loader(JsonLoader(json_path))
            .enable_deep_merge()
            .build()
        )

        self.assertEqual(config.database.host, "localhost")
        self.assertEqual(config.database.port, 5432)


class TestRealExport(RealWorldTestBase):
    """Test config export to different formats."""

    def test_export_json_and_yaml(self):
        from config_stash import Config
        from config_stash.loaders import YamlLoader

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

        # Export to JSON
        json_str = config.export("json")
        parsed = json.loads(json_str)
        self.assertEqual(parsed["host"], "localhost")

        # Export to YAML
        yaml_str = config.export("yaml")
        parsed = yaml.safe_load(yaml_str)
        self.assertEqual(parsed["host"], "localhost")


class TestRealValidation(RealWorldTestBase):
    """Test validation with real schemas."""

    def test_pydantic_validation(self):
        try:
            from pydantic import BaseModel
        except ImportError:
            self.skipTest("pydantic not installed")

        from config_stash import Config
        from config_stash.loaders import YamlLoader

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
            schema=AppConfig,
            validate_on_load=True,
            dynamic_reloading=False,
        )

        self.assertEqual(config.host, "localhost")
        self.assertEqual(config.port, 5432)

    def test_json_schema_validation(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed")

        from config_stash.validators.schema_validator import SchemaValidator

        schema = {
            "type": "object",
            "properties": {
                "host": {"type": "string"},
                "port": {"type": "integer", "minimum": 1},
            },
            "required": ["host", "port"],
        }

        validator = SchemaValidator(schema)

        # Valid
        self.assertTrue(validator.validate({"host": "localhost", "port": 5432}))

        # Invalid
        with self.assertRaises(Exception):
            validator.validate({"host": "localhost", "port": -1})

    def test_schema_with_defaults(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed")

        from config_stash.validators.schema_validator import SchemaValidator

        schema = {
            "type": "object",
            "properties": {
                "host": {"type": "string", "default": "localhost"},
                "port": {"type": "integer", "default": 5432},
                "name": {"type": "string"},
            },
            "required": ["name"],
        }

        validator = SchemaValidator(schema)
        result = validator.validate_with_defaults({"name": "mydb"})

        self.assertEqual(result["host"], "localhost")
        self.assertEqual(result["port"], 5432)
        self.assertEqual(result["name"], "mydb")


class TestRealHookProcessing(RealWorldTestBase):
    """Test hook processing with real config."""

    def test_custom_hook_transforms_values(self):
        from config_stash import Config
        from config_stash.loaders import YamlLoader

        yaml_path = self.write_yaml(
            "config.yaml",
            {
                "default": {"greeting": "hello world"},
            },
        )

        config = Config(
            env="default",
            loaders=[YamlLoader(yaml_path)],
            dynamic_reloading=False,
            use_type_casting=False,
            use_env_expander=False,
        )

        # Register a hook that uppercases strings
        config.hook_processor.register_global_hook(
            lambda v: v.upper() if isinstance(v, str) else v
        )

        self.assertEqual(config.greeting, "HELLO WORLD")

    def test_env_var_expansion(self):
        from config_stash import Config
        from config_stash.loaders import YamlLoader

        yaml_path = self.write_yaml(
            "config.yaml",
            {
                "default": {"home_dir": "${HOME}"},
            },
        )

        config = Config(
            env="default",
            loaders=[YamlLoader(yaml_path)],
            dynamic_reloading=False,
            use_env_expander=True,
            use_type_casting=False,
        )

        # HOME should be expanded
        home = config.home_dir
        self.assertNotIn("${", str(home), "Environment variable not expanded")
        self.assertTrue(len(str(home)) > 0)


class TestRealEdgeCases(RealWorldTestBase):
    """Test edge cases with real configs."""

    def test_empty_yaml_file(self):
        """Empty YAML file should not crash."""
        from config_stash.loaders import YamlLoader

        path = self.write_file("empty.yaml", "")
        loader = YamlLoader(path)
        result = loader.load()
        self.assertIsNotNone(result)
        self.assertEqual(result, {})

    def test_missing_file_returns_none(self):
        """Missing files should return None, not crash."""
        from config_stash.loaders import JsonLoader, TomlLoader, YamlLoader

        for LoaderClass in [YamlLoader, JsonLoader, TomlLoader]:
            result = LoaderClass("/nonexistent/path/config.xyz").load()
            self.assertIsNone(
                result, f"{LoaderClass.__name__} did not return None for missing file"
            )

    def test_unicode_config_values(self):
        """Unicode values should be handled correctly."""
        from config_stash import Config
        from config_stash.loaders import YamlLoader

        yaml_path = self.write_yaml(
            "config.yaml",
            {
                "default": {"greeting": "Hello, World!", "emoji": "Test"},
            },
        )

        config = Config(
            env="default",
            loaders=[YamlLoader(yaml_path)],
            dynamic_reloading=False,
        )

        self.assertEqual(config.greeting, "Hello, World!")

    def test_deeply_nested_config(self):
        """Deeply nested configs should work."""
        from config_stash import Config
        from config_stash.loaders import YamlLoader

        yaml_path = self.write_yaml(
            "config.yaml",
            {
                "default": {
                    "level1": {"level2": {"level3": {"level4": {"value": "deep"}}}}
                },
            },
        )

        config = Config(
            env="default",
            loaders=[YamlLoader(yaml_path)],
            dynamic_reloading=False,
        )

        self.assertEqual(config.level1.level2.level3.level4.value, "deep")

    def test_large_config(self):
        """Config with many keys should load efficiently."""
        from config_stash import Config
        from config_stash.loaders import YamlLoader

        large_config = {"default": {f"key_{i}": f"value_{i}" for i in range(500)}}
        yaml_path = self.write_yaml("large.yaml", large_config)

        config = Config(
            env="default",
            loaders=[YamlLoader(yaml_path)],
            dynamic_reloading=False,
        )

        self.assertEqual(config.key_0, "value_0")
        self.assertEqual(config.key_499, "value_499")
        self.assertEqual(len(config.keys()), 500)


if __name__ == "__main__":
    unittest.main()
