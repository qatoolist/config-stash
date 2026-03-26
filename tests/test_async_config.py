"""Tests for async configuration support."""

import asyncio
import os
import tempfile
import unittest

import yaml

from config_stash.async_config import (
    AsyncConfig,
    AsyncHTTPLoader,
    AsyncLoader,
    AsyncYamlLoader,
)


class TestAsyncYamlLoader(unittest.TestCase):
    """Test async YAML loader."""


    def test_async_yaml_loader_initialization(self):
        """Test initializing async YAML loader."""
        loader = AsyncYamlLoader("test.yaml")
        self.assertEqual(loader.source, "test.yaml")
        self.assertEqual(loader.config, {})

    def test_async_yaml_loader_load(self):
        """Test loading YAML file asynchronously."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"key1": "value1", "key2": "value2"}, f)
            temp_path = f.name

        try:

            async def test():
                loader = AsyncYamlLoader(temp_path)
                result = await loader.load()
                self.assertIsNotNone(result)
                self.assertEqual(result["key1"], "value1")
                self.assertEqual(result["key2"], "value2")

            asyncio.run(test())
        finally:
            os.unlink(temp_path)

    def test_async_yaml_loader_missing_file(self):
        """Test loading non-existent file returns None."""

        async def test():
            loader = AsyncYamlLoader("nonexistent.yaml")
            result = await loader.load()
            self.assertIsNone(result)

        asyncio.run(test())


class TestAsyncConfig(unittest.TestCase):
    """Test async configuration class."""

    def test_async_config_initialization(self):
        """Test initializing async config."""
        config = AsyncConfig(env="test")
        self.assertEqual(config.env, "test")
        self.assertEqual(config._config, None)

    def test_async_config_create(self):
        """Test creating async config with loaders."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"database": {"host": "localhost"}}, f)
            temp_path = f.name

        try:

            async def test():
                loader = AsyncYamlLoader(temp_path)
                config = await AsyncConfig.create(env="test", loaders=[loader])
                self.assertIsNotNone(config._config)
                self.assertEqual(config.env, "test")

            asyncio.run(test())
        finally:
            os.unlink(temp_path)

    def test_async_config_get_async(self):
        """Test getting configuration values asynchronously."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"database": {"host": "localhost", "port": 5432}}, f)
            temp_path = f.name

        try:

            async def test():
                loader = AsyncYamlLoader(temp_path)
                config = await AsyncConfig.create(env="test", loaders=[loader])
                host = await config.get_async("database.host")
                port = await config.get_async("database.port")
                self.assertEqual(host, "localhost")
                self.assertEqual(port, 5432)

            asyncio.run(test())
        finally:
            os.unlink(temp_path)

    def test_async_config_get_async_default(self):
        """Test getting configuration values with default."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"database": {"host": "localhost"}}, f)
            temp_path = f.name

        try:

            async def test():
                loader = AsyncYamlLoader(temp_path)
                config = await AsyncConfig.create(env="test", loaders=[loader])
                value = await config.get_async("database.missing", "default")
                self.assertEqual(value, "default")

            asyncio.run(test())
        finally:
            os.unlink(temp_path)

    def test_async_config_reload(self):
        """Test reloading configuration asynchronously."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"key": "value1"}, f)
            temp_path = f.name

        try:

            async def test():
                loader = AsyncYamlLoader(temp_path)
                config = await AsyncConfig.create(env="test", loaders=[loader])
                initial_value = await config.get_async("key")

                # Update file
                with open(temp_path, "w") as f:
                    yaml.dump({"key": "value2"}, f)

                await config.reload()
                new_value = await config.get_async("key")
                self.assertNotEqual(initial_value, new_value)
                self.assertEqual(new_value, "value2")

            asyncio.run(test())
        finally:
            os.unlink(temp_path)

    def test_async_config_to_dict(self):
        """Test converting async config to dictionary."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"key": "value"}, f)
            temp_path = f.name

        try:

            async def test():
                loader = AsyncYamlLoader(temp_path)
                config = await AsyncConfig.create(env="test", loaders=[loader])
                config_dict = config.to_dict()
                self.assertEqual(config_dict["key"], "value")

            asyncio.run(test())
        finally:
            os.unlink(temp_path)

    def test_async_config_parallel_loading(self):
        """Test loading multiple configs in parallel."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config1_path = os.path.join(tmpdir, "config1.yaml")
            config2_path = os.path.join(tmpdir, "config2.yaml")

            with open(config1_path, "w") as f:
                yaml.dump({"key1": "value1"}, f)
            with open(config2_path, "w") as f:
                yaml.dump({"key2": "value2"}, f)

            async def test():
                loaders = [AsyncYamlLoader(config1_path), AsyncYamlLoader(config2_path)]
                config = await AsyncConfig.create(env="test", loaders=loaders)
                value1 = await config.get_async("key1")
                value2 = await config.get_async("key2")
                self.assertEqual(value1, "value1")
                self.assertEqual(value2, "value2")

            asyncio.run(test())


if __name__ == "__main__":
    unittest.main()
