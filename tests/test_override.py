"""Tests for the Config.override() context manager."""

import os
import tempfile
import threading

import pytest
import yaml

from config_stash import Config
from config_stash.loaders.yaml_loader import YamlLoader


@pytest.fixture
def config_yaml(tmp_path):
    """Create a temporary YAML config file and return its path."""
    config_data = {
        "database": {
            "host": "localhost",
            "port": 5432,
            "name": "mydb",
        },
        "debug": False,
        "feature_flags": {
            "new_ui": True,
            "beta": False,
        },
    }
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump(config_data))
    return str(config_file)


@pytest.fixture
def config(config_yaml):
    """Create a Config instance from the temp YAML file."""
    return Config(loaders=[YamlLoader(config_yaml)])


@pytest.fixture
def config_override(config):
    """Fixture that provides config.override as a context manager."""
    return config.override


class TestOverrideBasic:
    """Basic override and restore behaviour."""

    def test_override_single_key(self, config):
        assert config.get("database.host") == "localhost"
        with config.override({"database.host": "test-db"}):
            assert config.get("database.host") == "test-db"
        assert config.get("database.host") == "localhost"

    def test_override_multiple_keys(self, config):
        with config.override({"database.host": "test-db", "debug": True}):
            assert config.get("database.host") == "test-db"
            assert config.get("debug") is True
        assert config.get("database.host") == "localhost"
        assert config.get("debug") is False

    def test_override_restores_on_exit(self, config):
        original_host = config.get("database.host")
        original_port = config.get("database.port")
        with config.override({"database.host": "overridden", "database.port": 9999}):
            pass
        assert config.get("database.host") == original_host
        assert config.get("database.port") == original_port


class TestOverrideNested:
    """Nested context manager support."""

    def test_nested_override(self, config):
        with config.override({"database.host": "test-db"}):
            assert config.get("database.host") == "test-db"
            with config.override({"database.port": 9999}):
                assert config.get("database.host") == "test-db"
                assert config.get("database.port") == 9999
            # port restored, host still overridden
            assert config.get("database.host") == "test-db"
            assert config.get("database.port") == 5432
        # everything restored
        assert config.get("database.host") == "localhost"
        assert config.get("database.port") == 5432

    def test_nested_override_same_key(self, config):
        """Inner override of same key should restore to outer's value."""
        with config.override({"database.host": "outer"}):
            assert config.get("database.host") == "outer"
            with config.override({"database.host": "inner"}):
                assert config.get("database.host") == "inner"
            assert config.get("database.host") == "outer"
        assert config.get("database.host") == "localhost"


class TestOverrideFrozen:
    """Override must work with frozen configs."""

    def test_override_frozen_config(self, config):
        config.freeze()
        assert config.is_frozen
        with config.override({"database.host": "frozen-override"}):
            assert config.get("database.host") == "frozen-override"
            # Should still be frozen inside the override (no set allowed)
            assert config.is_frozen
        assert config.get("database.host") == "localhost"
        assert config.is_frozen

    def test_override_frozen_config_restores_frozen_state(self, config):
        config.freeze()
        with config.override({"debug": True}):
            pass
        assert config.is_frozen


class TestOverrideExceptionSafety:
    """Values restored even when exceptions occur."""

    def test_restore_on_exception(self, config):
        original_host = config.get("database.host")
        with pytest.raises(ValueError, match="boom"):
            with config.override({"database.host": "bad-host"}):
                assert config.get("database.host") == "bad-host"
                raise ValueError("boom")
        assert config.get("database.host") == original_host

    def test_restore_on_exception_nested(self, config):
        with config.override({"database.host": "outer"}):
            with pytest.raises(RuntimeError):
                with config.override({"database.host": "inner"}):
                    raise RuntimeError("fail")
            # Inner restored, outer still active
            assert config.get("database.host") == "outer"
        assert config.get("database.host") == "localhost"


class TestOverrideAttributeAccess:
    """Override works with attribute-style access (config.x)."""

    def test_attribute_access_override(self, config):
        assert config.database.host == "localhost"
        with config.override({"database.host": "attr-test"}):
            assert config.database.host == "attr-test"
        assert config.database.host == "localhost"

    def test_attribute_access_top_level(self, config):
        assert config.debug is False
        with config.override({"debug": True}):
            assert config.debug is True
        assert config.debug is False

    def test_attribute_access_nested_dict(self, config):
        assert config.feature_flags.new_ui is True
        with config.override({"feature_flags.new_ui": False}):
            assert config.feature_flags.new_ui is False
        assert config.feature_flags.new_ui is True


class TestOverrideViaAlias:
    """Override works when config_stash is imported as cs."""

    def test_override_via_cs_import(self, config_yaml):
        import config_stash as cs

        cfg = cs.Config(loaders=[YamlLoader(config_yaml)])
        assert cfg.get("database.host") == "localhost"
        with cfg.override({"database.host": "cs-alias-test"}):
            assert cfg.get("database.host") == "cs-alias-test"
        assert cfg.get("database.host") == "localhost"


class TestOverrideFixture:
    """Test the config_override fixture pattern."""

    def test_fixture_usage(self, config_override):
        with config_override({"database.host": "fixture-test"}):
            pass  # Would test inside a real app

    def test_fixture_is_callable(self, config_override):
        assert callable(config_override)
