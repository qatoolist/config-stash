"""Tests for Config[T] typed configuration access."""

import os
import shutil
import tempfile
import unittest

import yaml


class TestTypedConfig(unittest.TestCase):
    """Test the Config[T].typed property for type-safe access."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def write_yaml(self, name, data):
        path = os.path.join(self.temp_dir, name)
        with open(path, "w") as f:
            yaml.dump(data, f)
        return path

    def test_typed_returns_pydantic_model(self):
        """config.typed returns a validated Pydantic model instance."""
        try:
            from pydantic import BaseModel
        except ImportError:
            self.skipTest("pydantic not installed")

        from config_stash import Config
        from config_stash.loaders import YamlLoader

        class AppConfig(BaseModel):
            host: str
            port: int
            debug: bool = False

        path = self.write_yaml("config.yaml", {
            "default": {"host": "localhost", "port": 5432, "debug": True},
        })

        config = Config[AppConfig](
            env="default",
            loaders=[YamlLoader(path)],
            schema=AppConfig,
            validate_on_load=True,
            dynamic_reloading=False,
        )

        # .typed returns the Pydantic model
        typed = config.typed
        self.assertIsInstance(typed, AppConfig)
        self.assertEqual(typed.host, "localhost")
        self.assertEqual(typed.port, 5432)
        self.assertTrue(typed.debug)

    def test_typed_with_nested_models(self):
        """Nested Pydantic models work with .typed."""
        try:
            from pydantic import BaseModel
        except ImportError:
            self.skipTest("pydantic not installed")

        from config_stash import Config
        from config_stash.loaders import YamlLoader

        class DatabaseConfig(BaseModel):
            host: str = "localhost"
            port: int = 5432

        class AppConfig(BaseModel):
            database: DatabaseConfig
            debug: bool = False

        path = self.write_yaml("config.yaml", {
            "default": {
                "database": {"host": "prod.db", "port": 3306},
                "debug": False,
            },
        })

        config = Config[AppConfig](
            env="default",
            loaders=[YamlLoader(path)],
            schema=AppConfig,
            validate_on_load=True,
            dynamic_reloading=False,
        )

        typed = config.typed
        self.assertIsInstance(typed.database, DatabaseConfig)
        self.assertEqual(typed.database.host, "prod.db")
        self.assertEqual(typed.database.port, 3306)

    def test_typed_auto_validates_on_first_access(self):
        """If validate_on_load=False, .typed auto-validates on first access."""
        try:
            from pydantic import BaseModel
        except ImportError:
            self.skipTest("pydantic not installed")

        from config_stash import Config
        from config_stash.loaders import YamlLoader

        class SimpleConfig(BaseModel):
            name: str

        path = self.write_yaml("config.yaml", {
            "default": {"name": "myapp"},
        })

        config = Config[SimpleConfig](
            env="default",
            loaders=[YamlLoader(path)],
            schema=SimpleConfig,
            validate_on_load=False,  # Not validated at load time
            dynamic_reloading=False,
        )

        # _validated_model is None before first access
        self.assertIsNone(config._validated_model)

        # .typed triggers auto-validation
        typed = config.typed
        self.assertEqual(typed.name, "myapp")
        self.assertIsNotNone(config._validated_model)

    def test_typed_raises_without_schema(self):
        """Accessing .typed without schema raises ValueError."""
        from config_stash import Config
        from config_stash.loaders import YamlLoader

        path = self.write_yaml("config.yaml", {
            "default": {"host": "localhost"},
        })

        config = Config(
            env="default",
            loaders=[YamlLoader(path)],
            dynamic_reloading=False,
        )

        with self.assertRaises(ValueError) as ctx:
            _ = config.typed

        self.assertIn("No schema provided", str(ctx.exception))

    def test_typed_coexists_with_untyped_access(self):
        """Both config.typed.x and config.x work simultaneously."""
        try:
            from pydantic import BaseModel
        except ImportError:
            self.skipTest("pydantic not installed")

        from config_stash import Config
        from config_stash.loaders import YamlLoader

        class AppConfig(BaseModel):
            host: str
            port: int

        path = self.write_yaml("config.yaml", {
            "default": {"host": "localhost", "port": 5432},
        })

        config = Config[AppConfig](
            env="default",
            loaders=[YamlLoader(path)],
            schema=AppConfig,
            validate_on_load=True,
            dynamic_reloading=False,
        )

        # Typed access
        self.assertEqual(config.typed.host, "localhost")
        # Untyped access still works
        self.assertEqual(config.host, "localhost")

    def test_typed_with_cs_alias(self):
        """Config[T] works through the cs alias."""
        try:
            from pydantic import BaseModel
        except ImportError:
            self.skipTest("pydantic not installed")

        from cs import Config
        from cs.loaders import YamlLoader

        class MyConfig(BaseModel):
            name: str = "default"

        path = self.write_yaml("config.yaml", {
            "default": {"name": "test-app"},
        })

        config = Config[MyConfig](
            env="default",
            loaders=[YamlLoader(path)],
            schema=MyConfig,
            validate_on_load=True,
            dynamic_reloading=False,
        )

        self.assertEqual(config.typed.name, "test-app")

    def test_typed_after_reload(self):
        """After reload with validation, .typed reflects new values."""
        try:
            from pydantic import BaseModel
        except ImportError:
            self.skipTest("pydantic not installed")

        from config_stash import Config
        from config_stash.loaders import YamlLoader

        class AppConfig(BaseModel):
            host: str

        path = self.write_yaml("config.yaml", {
            "default": {"host": "original"},
        })

        config = Config[AppConfig](
            env="default",
            loaders=[YamlLoader(path)],
            schema=AppConfig,
            validate_on_load=True,
            dynamic_reloading=False,
        )

        self.assertEqual(config.typed.host, "original")

        # Modify file and reload
        self.write_yaml("config.yaml", {
            "default": {"host": "reloaded"},
        })
        config.reload(validate=True)

        self.assertEqual(config.typed.host, "reloaded")


if __name__ == "__main__":
    unittest.main()
