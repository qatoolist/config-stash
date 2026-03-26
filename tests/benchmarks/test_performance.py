"""Performance benchmarks for Config-Stash.

Run with: pytest tests/benchmarks/test_performance.py --benchmark-only
"""


import tempfile
from pathlib import Path

import pytest

try:
    import pytest_benchmark

    HAS_BENCHMARK = True
except ImportError:
    HAS_BENCHMARK = False
    pytest.skip("pytest-benchmark not installed", allow_module_level=True)


@pytest.mark.benchmark
class TestConfigPerformance:
    """Performance benchmarks for Config operations."""

    @pytest.fixture
    def large_config_file(self, tmp_path):
        """Create a large configuration file for testing."""
        config_file = tmp_path / "large_config.yaml"
        config_data = {}

        # Generate large config (100 top-level keys, each with 50 nested keys)
        for i in range(100):
            key = f"section_{i}"
            config_data[key] = {}
            for j in range(50):
                config_data[key][f"key_{j}"] = f"value_{i}_{j}"

        import yaml

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        return str(config_file)

    @pytest.fixture
    def multiple_config_files(self, tmp_path):
        """Create multiple configuration files for merge testing."""
        files = []
        for i in range(10):
            config_file = tmp_path / f"config_{i}.yaml"
            import yaml

            with open(config_file, "w") as f:
                yaml.dump({f"key_{i}": f"value_{i}"}, f)
            files.append(str(config_file))
        return files

    def test_config_initialization(self, large_config_file, benchmark):
        """Benchmark Config initialization with large config file."""
        from config_stash import Config
        from config_stash.loaders import YamlLoader

        def init_config():
            return Config(
                loaders=[YamlLoader(large_config_file)], enable_ide_support=False
            )

        benchmark(init_config)

    def test_config_access(self, large_config_file, benchmark):
        """Benchmark accessing configuration values."""
        from config_stash import Config
        from config_stash.loaders import YamlLoader

        config = Config(
            loaders=[YamlLoader(large_config_file)], enable_ide_support=False
        )

        def access_value():
            return config.section_0.key_0

        benchmark(access_value)

    def test_config_merge(self, multiple_config_files, benchmark):
        """Benchmark merging multiple configuration files."""
        from config_stash import Config
        from config_stash.loaders import YamlLoader

        loaders = [YamlLoader(f) for f in multiple_config_files]

        def merge_configs():
            return Config(loaders=loaders, enable_ide_support=False)

        benchmark(merge_configs)

    def test_config_reload(self, large_config_file, benchmark):
        """Benchmark reloading configuration."""
        from config_stash import Config
        from config_stash.loaders import YamlLoader

        config = Config(
            loaders=[YamlLoader(large_config_file)],
            enable_ide_support=False,
            dynamic_reloading=False,
        )

        def reload_config():
            config.reload(incremental=False)

        benchmark(reload_config)

    def test_config_introspection(self, large_config_file, benchmark):
        """Benchmark configuration introspection methods."""
        from config_stash import Config
        from config_stash.loaders import YamlLoader

        config = Config(
            loaders=[YamlLoader(large_config_file)], enable_ide_support=False
        )

        def get_all_keys():
            return config.keys()

        benchmark(get_all_keys)

    def test_config_get_with_default(self, large_config_file, benchmark):
        """Benchmark get() method with defaults."""
        from config_stash import Config
        from config_stash.loaders import YamlLoader

        config = Config(
            loaders=[YamlLoader(large_config_file)], enable_ide_support=False
        )

        def get_with_default():
            return config.get("non.existent.key", "default_value")

        benchmark(get_with_default)
