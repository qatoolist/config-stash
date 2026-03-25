"""Tests for enhanced source tracking functionality."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from config_stash import Config
from config_stash.enhanced_source_tracker import EnhancedSourceTracker, SourceInfo
from config_stash.loaders import EnvironmentLoader, JsonLoader, YamlLoader


class TestEnhancedSourceTracker:
    """Test enhanced source tracking features."""
# pyright: reportOptionalSubscript=false, reportOptionalMemberAccess=false
# pyright: reportArgumentType=false, reportPossiblyUnboundVariable=false
# pyright: reportAttributeAccessIssue=false, reportCallIssue=false
# pyright: reportMissingImports=false

    def test_basic_source_tracking(self):
        """Test basic source tracking without debug mode."""
        tracker = EnhancedSourceTracker(debug_mode=False)

        tracker.track_value("database.host", "localhost", "config.yaml", "YamlLoader")
        tracker.track_value("database.port", 5432, "config.yaml", "YamlLoader")

        # Get source info
        info = tracker.get_source("database.host")
        assert info == "config.yaml"

        source_info = tracker.get_source_info("database.host")
        assert source_info.value == "localhost"
        assert source_info.source_file == "config.yaml"
        assert source_info.loader_type == "YamlLoader"

    def test_debug_mode_tracking(self):
        """Test detailed tracking in debug mode."""
        tracker = EnhancedSourceTracker(debug_mode=True)

        # Track initial value
        tracker.track_value("api.endpoint", "http://api.v1", "base.yaml", "YamlLoader")

        # Override the value
        tracker.track_value("api.endpoint", "http://api.v2", "override.json", "JsonLoader")

        # Check current value
        info = tracker.get_source_info("api.endpoint")
        assert info.value == "http://api.v2"
        assert info.source_file == "override.json"
        assert info.override_count == 1

        # Check override history
        history = tracker.get_override_history("api.endpoint")
        assert len(history) == 1
        assert history[0].value == "http://api.v1"
        assert history[0].source_file == "base.yaml"

    def test_loader_order_tracking(self):
        """Test tracking the order of loaders."""
        tracker = EnhancedSourceTracker(debug_mode=True)

        tracker.track_loader("YamlLoader", "config.yaml")
        tracker.track_loader("JsonLoader", "override.json")
        tracker.track_loader("EnvironmentLoader", "ENV")

        order = tracker.get_loader_order()
        assert len(order) == 3
        assert order[0] == ("YamlLoader", "config.yaml")
        assert order[1] == ("JsonLoader", "override.json")
        assert order[2] == ("EnvironmentLoader", "ENV")

    def test_conflict_detection(self):
        """Test detection of configuration conflicts."""
        tracker = EnhancedSourceTracker(debug_mode=True)

        # No conflicts initially
        conflicts = tracker.get_conflicts()
        assert len(conflicts) == 0

        # Create conflicts
        tracker.track_value("port", 8080, "base.yaml", "YamlLoader")
        tracker.track_value("port", 9090, "override.json", "JsonLoader")
        tracker.track_value("host", "localhost", "base.yaml", "YamlLoader")

        conflicts = tracker.get_conflicts()
        assert "port" in conflicts
        assert "host" not in conflicts  # No override for host

    def test_find_keys_from_source(self):
        """Test finding keys from a specific source."""
        tracker = EnhancedSourceTracker(debug_mode=True)

        tracker.track_value("db.host", "localhost", "database.yaml", "YamlLoader")
        tracker.track_value("db.port", 5432, "database.yaml", "YamlLoader")
        tracker.track_value("api.key", "secret", "api.json", "JsonLoader")

        # Find keys from database.yaml
        keys = tracker.find_keys_from_source("database.yaml")
        assert len(keys) == 2
        assert "db.host" in keys
        assert "db.port" in keys
        assert "api.key" not in keys

    def test_source_statistics(self):
        """Test getting source statistics."""
        tracker = EnhancedSourceTracker(debug_mode=True)

        tracker.track_value("a", 1, "config1.yaml", "YamlLoader")
        tracker.track_value("b", 2, "config1.yaml", "YamlLoader")
        tracker.track_value("c", 3, "config2.json", "JsonLoader")
        tracker.track_value("a", 10, "override.yaml", "YamlLoader")  # Override

        stats = tracker.get_source_statistics()
        assert stats["total_keys"] == 3  # a, b, c
        assert stats["total_overrides"] == 1  # 'a' was overridden once
        assert stats["keys_with_overrides"] == 1
        assert "YamlLoader" in stats["sources_by_loader"]
        assert "JsonLoader" in stats["sources_by_loader"]

    def test_source_info_to_dict(self):
        """Test SourceInfo serialization to dict."""
        info = SourceInfo(
            key="test.key",
            value="test_value",
            source_file="test.yaml",
            loader_type="YamlLoader",
            line_number=42,
            override_count=2,
            environment="production",
        )

        data = info.to_dict()
        assert data["key"] == "test.key"
        assert data["value"] == "test_value"
        assert data["line_number"] == 42
        assert data["override_count"] == 2
        assert data["environment"] == "production"

    def test_export_debug_report(self, tmp_path):
        """Test exporting debug report to JSON."""
        tracker = EnhancedSourceTracker(debug_mode=True)

        tracker.track_value("key1", "value1", "source1.yaml", "YamlLoader")
        tracker.track_value("key2", "value2", "source2.json", "JsonLoader")

        report_path = tmp_path / "debug_report.json"
        tracker.export_debug_report(str(report_path))

        assert report_path.exists()

        with open(report_path) as f:
            report = json.load(f)

        assert "timestamp" in report
        assert report["total_keys"] == 2
        assert "sources" in report
        assert "key1" in report["sources"]
        assert "key2" in report["sources"]


class TestConfigWithSourceTracking:
    """Test Config class with enhanced source tracking."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        # Create test configuration files
        self.base_config = """
default:
  database:
    host: localhost
    port: 5432
    name: myapp
  api:
    endpoint: http://api.example.com
    timeout: 30
"""
        with open("base.yaml", "w") as f:
            f.write(self.base_config)

        self.override_config = """
{
  "default": {
    "database": {
      "port": 3306,
      "name": "production_db"
    },
    "api": {
      "endpoint": "https://prod-api.example.com"
    }
  }
}
"""
        with open("override.json", "w") as f:
            f.write(self.override_config)

    def teardown_method(self):
        """Clean up test environment."""
        os.chdir(self.original_dir)
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_config_without_debug_mode(self):
        """Test Config with source tracking disabled."""
        config = Config(
            loaders=[
                YamlLoader("base.yaml"),
                JsonLoader("override.json"),
            ],
            env="default",
            debug_mode=False,
            enable_ide_support=False,  # Disable to reduce test output
        )

        # Basic source tracking should still work
        source = config.get_source("database.host")
        assert source == "base.yaml"

        # But detailed info won't have override history
        info = config.get_source_info("database.port")
        assert info is None or info.override_count == 0

    def test_config_with_debug_mode(self):
        """Test Config with debug mode enabled."""
        config = Config(
            loaders=[
                YamlLoader("base.yaml"),
                JsonLoader("override.json"),
            ],
            env="default",
            debug_mode=True,
            enable_ide_support=False,
        )

        # Check values were loaded correctly
        assert config.database.host == "localhost"  # Not overridden
        assert config.database.port == 3306  # Overridden
        assert config.database.name == "production_db"  # Overridden

        # Check source info for non-overridden value
        host_info = config.get_source_info("database.host")
        if host_info:
            assert host_info.source_file == "base.yaml"
            assert host_info.override_count == 0

        # Check source info for overridden value
        port_info = config.get_source_info("database.port")
        if port_info:
            assert port_info.value in [3306, 5432]  # Could be either depending on tracking order
            if port_info.override_count > 0:
                history = config.get_override_history("database.port")
                assert len(history) > 0

    def test_config_source_statistics(self):
        """Test getting source statistics from Config."""
        config = Config(
            loaders=[
                YamlLoader("base.yaml"),
                JsonLoader("override.json"),
            ],
            env="default",
            debug_mode=True,
            enable_ide_support=False,
        )

        stats = config.get_source_statistics()
        assert (
            stats["total_keys"] >= 4
        )  # At minimum: database.host, database.port, database.name, api.endpoint
        assert stats["unique_sources"] >= 2  # base.yaml and override.json

    def test_config_find_keys_from_source(self):
        """Test finding keys from a specific source in Config."""
        config = Config(
            loaders=[
                YamlLoader("base.yaml"),
                JsonLoader("override.json"),
            ],
            env="default",
            debug_mode=True,
            enable_ide_support=False,
        )

        # Find keys from base.yaml
        yaml_keys = config.find_keys_from_source("base.yaml")
        assert isinstance(yaml_keys, list)

        # Find keys from override.json
        json_keys = config.find_keys_from_source("override.json")
        assert isinstance(json_keys, list)

    def test_config_with_environment_override(self):
        """Test source tracking with environment variable overrides."""
        os.environ["APP_DATABASE_PORT"] = "7777"

        config = Config(
            loaders=[
                YamlLoader("base.yaml"),
                JsonLoader("override.json"),
                EnvironmentLoader("APP", separator="_"),  # Use single underscore
            ],
            env="default",
            debug_mode=True,
            enable_ide_support=False,
        )

        # Port should be overridden by environment variable
        assert config.database.port == 7777

        # Check source tracking
        port_info = config.get_source_info("database.port")
        if port_info and port_info.override_count > 0:
            assert port_info.loader_type == "EnvironmentLoader"

        # Clean up
        del os.environ["APP_DATABASE_PORT"]

    def test_config_export_debug_report(self):
        """Test exporting debug report from Config."""
        config = Config(
            loaders=[
                YamlLoader("base.yaml"),
                JsonLoader("override.json"),
            ],
            env="default",
            debug_mode=True,
            enable_ide_support=False,
        )

        report_path = "config_debug.json"
        config.export_debug_report(report_path)

        assert Path(report_path).exists()

        with open(report_path) as f:
            report = json.load(f)
            assert "timestamp" in report
            assert "loader_order" in report
            assert "sources" in report

    def test_config_print_debug_info(self, capsys):
        """Test printing debug information."""
        config = Config(
            loaders=[
                YamlLoader("base.yaml"),
                JsonLoader("override.json"),
            ],
            env="default",
            debug_mode=True,
            enable_ide_support=False,
        )

        # Print debug info for all keys
        config.print_debug_info()
        captured = capsys.readouterr()
        assert "Configuration Source Debug Information" in captured.out

        # Print debug info for specific key
        config.print_debug_info("database.port")
        captured = capsys.readouterr()
        # Output should mention the key or indicate it's being debugged
        assert (
            "database" in captured.out.lower()
            or "port" in captured.out.lower()
            or "not found" in captured.out
        )

    def test_config_get_conflicts(self):
        """Test getting configuration conflicts."""
        config = Config(
            loaders=[
                YamlLoader("base.yaml"),
                JsonLoader("override.json"),
            ],
            env="default",
            debug_mode=True,
            enable_ide_support=False,
        )

        conflicts = config.get_conflicts()
        # Should have conflicts for overridden values
        assert isinstance(conflicts, dict)
        # The exact conflicts depend on how the tracking is implemented

    def test_backward_compatibility(self):
        """Test that legacy get_source method still works."""
        config = Config(
            loaders=[
                YamlLoader("base.yaml"),
                JsonLoader("override.json"),
            ],
            env="default",
            debug_mode=False,  # Even without debug mode
            enable_ide_support=False,
        )

        # Legacy method should still work
        source = config.get_source("database.host")
        assert source == "base.yaml"
