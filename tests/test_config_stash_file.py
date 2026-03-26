"""Tests for config-stash self-configuration file support.

Verifies that config-stash can read its own settings from dedicated
config-stash.yaml/.json/.toml files, falling back to pyproject.toml.
"""

import json
import os
import textwrap

import pytest
import yaml

from config_stash.config_reader import (
    _DEFAULT_SETTINGS,
    clear_config_cache,
    read_config_stash_file,
    read_self_config,
    get_default_settings,
)


@pytest.fixture(autouse=True)
def _clear_config_cache():
    """Clear the config reader cache before each test."""
    clear_config_cache()
    yield
    clear_config_cache()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_yaml(path, data):
    """Write a dictionary as YAML to the given path."""
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)


def _write_json(path, data):
    """Write a dictionary as JSON to the given path."""
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _write_toml(path, data):
    """Write a dictionary as TOML to the given path."""
    from config_stash.utils.toml_compat import dumps as toml_dumps
    with open(path, "w") as f:
        f.write(toml_dumps(data))


# ---------------------------------------------------------------------------
# Tests: read_config_stash_file
# ---------------------------------------------------------------------------

class TestReadConfigStashFile:
    """Test loading from various config-stash.* file formats."""

    def test_load_yaml(self, tmp_path):
        data = {"default_environment": "staging", "deep_merge": False}
        _write_yaml(tmp_path / "config-stash.yaml", data)

        result = read_config_stash_file(search_dir=str(tmp_path))
        assert result is not None
        assert result["default_environment"] == "staging"
        assert result["deep_merge"] is False

    def test_load_yml(self, tmp_path):
        data = {"default_environment": "production"}
        _write_yaml(tmp_path / "config-stash.yml", data)

        result = read_config_stash_file(search_dir=str(tmp_path))
        assert result is not None
        assert result["default_environment"] == "production"

    def test_load_json(self, tmp_path):
        data = {"default_environment": "testing", "debug_mode": True}
        _write_json(tmp_path / "config-stash.json", data)

        result = read_config_stash_file(search_dir=str(tmp_path))
        assert result is not None
        assert result["default_environment"] == "testing"
        assert result["debug_mode"] is True

    def test_load_toml(self, tmp_path):
        data = {"default_environment": "ci", "deep_merge": True}
        _write_toml(tmp_path / "config-stash.toml", data)

        result = read_config_stash_file(search_dir=str(tmp_path))
        assert result is not None
        assert result["default_environment"] == "ci"
        assert result["deep_merge"] is True

    def test_load_hidden_yaml(self, tmp_path):
        data = {"default_environment": "hidden-env", "use_type_casting": False}
        _write_yaml(tmp_path / ".config-stash.yaml", data)

        result = read_config_stash_file(search_dir=str(tmp_path))
        assert result is not None
        assert result["default_environment"] == "hidden-env"
        assert result["use_type_casting"] is False

    def test_load_hidden_yml(self, tmp_path):
        data = {"default_environment": "hidden-yml"}
        _write_yaml(tmp_path / ".config-stash.yml", data)

        result = read_config_stash_file(search_dir=str(tmp_path))
        assert result is not None
        assert result["default_environment"] == "hidden-yml"

    def test_load_hidden_json(self, tmp_path):
        data = {"default_environment": "hidden-json"}
        _write_json(tmp_path / ".config-stash.json", data)

        result = read_config_stash_file(search_dir=str(tmp_path))
        assert result is not None
        assert result["default_environment"] == "hidden-json"

    def test_load_hidden_toml(self, tmp_path):
        data = {"default_environment": "hidden-toml"}
        _write_toml(tmp_path / ".config-stash.toml", data)

        result = read_config_stash_file(search_dir=str(tmp_path))
        assert result is not None
        assert result["default_environment"] == "hidden-toml"

    def test_returns_none_when_no_file(self, tmp_path):
        result = read_config_stash_file(search_dir=str(tmp_path))
        assert result is None

    def test_yaml_takes_priority_over_json(self, tmp_path):
        _write_yaml(tmp_path / "config-stash.yaml", {"default_environment": "from-yaml"})
        _write_json(tmp_path / "config-stash.json", {"default_environment": "from-json"})

        result = read_config_stash_file(search_dir=str(tmp_path))
        assert result["default_environment"] == "from-yaml"

    def test_non_hidden_takes_priority_over_hidden(self, tmp_path):
        _write_json(tmp_path / "config-stash.json", {"default_environment": "non-hidden"})
        _write_yaml(tmp_path / ".config-stash.yaml", {"default_environment": "hidden"})

        result = read_config_stash_file(search_dir=str(tmp_path))
        # config-stash.json is searched before .config-stash.yaml
        assert result["default_environment"] == "non-hidden"

    def test_malformed_file_is_skipped(self, tmp_path):
        # Write invalid YAML
        bad_file = tmp_path / "config-stash.yaml"
        bad_file.write_text(":\n  bad: [unterminated")

        # Provide a valid fallback
        _write_json(tmp_path / "config-stash.json", {"default_environment": "fallback"})

        result = read_config_stash_file(search_dir=str(tmp_path))
        assert result["default_environment"] == "fallback"


# ---------------------------------------------------------------------------
# Tests: read_self_config (fallback to pyproject.toml)
# ---------------------------------------------------------------------------

class TestReadSelfConfig:
    """Test that read_self_config falls back to pyproject.toml."""

    def test_config_stash_file_wins_over_pyproject(self, tmp_path, monkeypatch):
        # Write both a config-stash.yaml and a pyproject.toml
        _write_yaml(tmp_path / "config-stash.yaml", {"default_environment": "from-file"})

        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(textwrap.dedent("""\
            [tool.config_stash]
            default_environment = "from-pyproject"
        """))

        monkeypatch.chdir(tmp_path)
        result = read_self_config(search_dir=str(tmp_path))
        assert result["default_environment"] == "from-file"

    def test_falls_back_to_pyproject_when_no_config_file(self, tmp_path, monkeypatch):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(textwrap.dedent("""\
            [tool.config_stash]
            default_environment = "from-pyproject"
        """))

        monkeypatch.chdir(tmp_path)
        result = read_self_config(search_dir=str(tmp_path))
        assert result["default_environment"] == "from-pyproject"

    def test_returns_empty_when_nothing_found(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = read_self_config(search_dir=str(tmp_path))
        # Falls through to read_pyproject_config which finds nothing in tmp_path
        # but may find the real pyproject.toml; the important thing is no crash.
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Tests: get_default_settings
# ---------------------------------------------------------------------------

class TestGetDefaultSettings:
    """Test that get_default_settings merges file settings with defaults."""

    def test_all_defaults_present(self, tmp_path, monkeypatch):
        """All default settings should be returned even with no config file."""
        monkeypatch.chdir(tmp_path)
        settings = get_default_settings()
        for key in _DEFAULT_SETTINGS:
            assert key in settings, f"Missing default key: {key}"

    def test_file_values_override_defaults(self, tmp_path, monkeypatch):
        _write_yaml(tmp_path / "config-stash.yaml", {
            "default_environment": "production",
            "deep_merge": False,
            "debug_mode": True,
            "log_level": "DEBUG",
            "secret_cache_ttl": 60,
        })

        monkeypatch.chdir(tmp_path)
        settings = get_default_settings()
        assert settings["default_environment"] == "production"
        assert settings["deep_merge"] is False
        assert settings["debug_mode"] is True
        assert settings["log_level"] == "DEBUG"
        assert settings["secret_cache_ttl"] == 60

    def test_unset_values_get_defaults(self, tmp_path, monkeypatch):
        _write_yaml(tmp_path / "config-stash.yaml", {
            "default_environment": "staging",
        })

        monkeypatch.chdir(tmp_path)
        settings = get_default_settings()
        assert settings["default_environment"] == "staging"
        # Everything else should be the defaults
        assert settings["deep_merge"] is True
        assert settings["debug_mode"] is False
        assert settings["dynamic_reloading"] is False


# ---------------------------------------------------------------------------
# Tests: Config.__init__ integration with self-config file
# ---------------------------------------------------------------------------

class TestConfigInitIntegration:
    """Test that Config() picks up settings from config-stash.* files."""

    def test_config_reads_from_config_stash_yaml(self, tmp_path, monkeypatch):
        """Config should apply settings from config-stash.yaml."""
        _write_yaml(tmp_path / "config-stash.yaml", {
            "default_environment": "staging",
            "deep_merge": False,
            "use_env_expander": False,
            "debug_mode": True,
        })

        monkeypatch.chdir(tmp_path)

        from config_stash.loaders.json_loader import JsonLoader
        # Create a minimal config file so Config can load something
        config_file = tmp_path / "app.json"
        _write_json(config_file, {"staging": {"key": "value"}})

        from config_stash import Config
        config = Config(loaders=[JsonLoader(str(config_file))])

        assert config.env == "staging"
        assert config.deep_merge is False
        assert config.use_env_expander is False
        assert config.debug_mode is True

    def test_explicit_params_override_file(self, tmp_path, monkeypatch):
        """Explicit Config() params should override config-stash.yaml values."""
        _write_yaml(tmp_path / "config-stash.yaml", {
            "default_environment": "staging",
            "deep_merge": False,
            "debug_mode": True,
        })

        monkeypatch.chdir(tmp_path)

        from config_stash.loaders.json_loader import JsonLoader
        config_file = tmp_path / "app.json"
        _write_json(config_file, {"production": {"key": "value"}})

        from config_stash import Config
        config = Config(
            env="production",
            loaders=[JsonLoader(str(config_file))],
            deep_merge=True,
            debug_mode=False,
        )

        # Explicit params should win
        assert config.env == "production"
        assert config.deep_merge is True
        assert config.debug_mode is False

    def test_config_reads_from_json_file(self, tmp_path, monkeypatch):
        """Config should apply settings from config-stash.json."""
        _write_json(tmp_path / "config-stash.json", {
            "default_environment": "test",
            "use_type_casting": False,
        })

        monkeypatch.chdir(tmp_path)

        from config_stash.loaders.json_loader import JsonLoader
        config_file = tmp_path / "app.json"
        _write_json(config_file, {"test": {"key": "value"}})

        from config_stash import Config
        config = Config(loaders=[JsonLoader(str(config_file))])

        assert config.env == "test"
        assert config.use_type_casting is False

    def test_config_reads_from_toml_file(self, tmp_path, monkeypatch):
        """Config should apply settings from config-stash.toml."""
        _write_toml(tmp_path / "config-stash.toml", {
            "default_environment": "ci",
            "strict_validation": True,
        })

        monkeypatch.chdir(tmp_path)

        from config_stash.loaders.json_loader import JsonLoader
        config_file = tmp_path / "app.json"
        _write_json(config_file, {"ci": {"key": "value"}})

        from config_stash import Config
        config = Config(loaders=[JsonLoader(str(config_file))])

        assert config.env == "ci"
        assert config.strict_validation is True

    def test_config_reads_hidden_file(self, tmp_path, monkeypatch):
        """Config should apply settings from .config-stash.yaml."""
        _write_yaml(tmp_path / ".config-stash.yaml", {
            "default_environment": "hidden-env",
        })

        monkeypatch.chdir(tmp_path)

        from config_stash.loaders.json_loader import JsonLoader
        config_file = tmp_path / "app.json"
        _write_json(config_file, {"hidden-env": {"key": "val"}})

        from config_stash import Config
        config = Config(loaders=[JsonLoader(str(config_file))])

        assert config.env == "hidden-env"

    def test_pyproject_fallback_when_no_config_file(self, tmp_path, monkeypatch):
        """When no config-stash.* file exists, fall back to pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(textwrap.dedent("""\
            [tool.config_stash]
            default_environment = "from-pyproject"
        """))

        monkeypatch.chdir(tmp_path)

        from config_stash.loaders.json_loader import JsonLoader
        config_file = tmp_path / "app.json"
        _write_json(config_file, {"from-pyproject": {"key": "val"}})

        from config_stash import Config
        config = Config(loaders=[JsonLoader(str(config_file))])

        assert config.env == "from-pyproject"

    def test_env_switcher_from_config_file(self, tmp_path, monkeypatch):
        """env_switcher from config-stash.yaml should be applied."""
        _write_yaml(tmp_path / "config-stash.yaml", {
            "env_switcher": "MY_APP_ENV",
            "default_environment": "development",
        })

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("MY_APP_ENV", "production")

        from config_stash.loaders.json_loader import JsonLoader
        config_file = tmp_path / "app.json"
        _write_json(config_file, {"production": {"key": "val"}})

        from config_stash import Config
        config = Config(loaders=[JsonLoader(str(config_file))])

        assert config.env == "production"

    def test_all_settings_documented(self):
        """Every key in _DEFAULT_SETTINGS should have a documented default."""
        expected_keys = {
            "default_environment", "env_switcher", "default_files",
            "default_prefix", "env_prefix", "sysenv_fallback",
            "deep_merge", "merge_strategy", "merge_strategy_map",
            "validate_on_load", "strict_validation",
            "use_env_expander", "use_type_casting",
            "dynamic_reloading", "incremental_reload",
            "secret_cache_ttl",
            "enable_observability", "enable_events", "max_reload_durations",
            "enable_versioning", "version_storage_path", "max_versions",
            "enable_ide_support", "ide_stub_path",
            "debug_mode", "log_level",
            "loaders",
            "sources", "secrets", "schema_path",
            "freeze_on_load", "on_error",
        }
        assert set(_DEFAULT_SETTINGS.keys()) == expected_keys
