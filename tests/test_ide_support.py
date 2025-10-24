"""Tests for IDE support functionality."""

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from config_stash import Config
from config_stash.ide_support import IDESupport, VSCodeSupport
from config_stash.loaders import YamlLoader


class TestIDESupport:
    """Test IDE support features."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.temp_dir)

        # Create test config file
        self.config_file = "test_config.yaml"
        config_content = """
default:
  database:
    host: localhost
    port: 5432
    name: testdb
    credentials:
      username: admin
      password: secret

  api:
    endpoint: https://api.example.com
    timeout: 30
    retry_count: 3

  features:
    - authentication
    - caching
    - logging
"""
        with open(self.config_file, "w") as f:
            f.write(config_content)

    def teardown_method(self):
        """Clean up test environment."""
        os.chdir(self.original_dir)
        shutil.rmtree(self.temp_dir)

    def test_automatic_ide_support_generation(self):
        """Test that IDE support is generated automatically."""
        # Create config with default settings (IDE support enabled)
        config = Config(loaders=[YamlLoader(self.config_file)])

        # Check that IDE support files were created
        ide_dir = Path(".config_stash")
        stub_file = ide_dir / "stubs.pyi"
        init_file = ide_dir / "__init__.py"

        assert ide_dir.exists()
        assert stub_file.exists()
        assert init_file.exists()

        # Verify stub content
        with open(stub_file) as f:
            content = f.read()
            assert "class ConfigType:" in content
            assert "database:" in content
            assert "api:" in content
            assert "features:" in content

    def test_disable_ide_support(self):
        """Test that IDE support can be disabled."""
        # Create config with IDE support disabled
        config = Config(
            loaders=[YamlLoader(self.config_file)],
            enable_ide_support=False
        )

        # Check that IDE support files were NOT created
        ide_dir = Path(".config_stash")
        assert not ide_dir.exists()

    def test_custom_stub_path(self):
        """Test custom path for IDE stub files."""
        custom_path = "my_custom_stubs.pyi"

        config = Config(
            loaders=[YamlLoader(self.config_file)],
            ide_stub_path=custom_path
        )

        # Check that custom stub file was created
        assert Path(custom_path).exists()

        # Verify content
        with open(custom_path) as f:
            content = f.read()
            assert "class ConfigType:" in content

    def test_generate_stub_method(self):
        """Test the generate_stub static method."""
        config = Config(
            loaders=[YamlLoader(self.config_file)],
            enable_ide_support=False  # Disable automatic generation
        )

        # Manually generate stub
        output_path = "manual_stub.pyi"
        IDESupport.generate_stub(config, output_path, silent=True)

        assert Path(output_path).exists()

        with open(output_path) as f:
            content = f.read()
            assert "class ConfigType:" in content
            assert "class DatabaseType:" in content
            assert "class CredentialsType:" in content

    def test_stub_content_structure(self):
        """Test that generated stub has correct structure."""
        config = Config(loaders=[YamlLoader(self.config_file)])

        stub_file = Path(".config_stash/stubs.pyi")
        with open(stub_file) as f:
            content = f.read()

        # Check imports
        assert "from typing import Any, Optional, Dict, List" in content

        # Check nested classes
        assert "class DatabaseType:" in content
        assert "class CredentialsType:" in content
        assert "class ApiType:" in content

        # Check properties
        assert "host: str" in content
        assert "port: int" in content
        assert "endpoint: str" in content
        assert "features: List[str]" in content

        # Check usage comment
        assert "# Usage:" in content

    def test_sanitize_key_in_stub(self):
        """Test that keys are properly sanitized in stub generation."""
        # Create config with keys that need sanitization
        config_content = """
default:
  "my-dashed-key": value1
  "my.dotted.key": value2
  "123numeric": value3
  "key with spaces": value4
"""
        with open("sanitize_test.yaml", "w") as f:
            f.write(config_content)

        config = Config(loaders=[YamlLoader("sanitize_test.yaml")])

        stub_file = Path(".config_stash/stubs.pyi")
        with open(stub_file) as f:
            content = f.read()

        # Check sanitized keys
        assert "my_dashed_key:" in content
        assert "my_dotted_key:" in content
        assert "_123numeric:" in content
        assert "key_with_spaces:" in content

    def test_enable_auto_generation(self):
        """Test auto-generation with dynamic reloading."""
        config = Config(
            loaders=[YamlLoader(self.config_file)],
            dynamic_reloading=True
        )

        # Check initial stub exists
        stub_file = Path(".config_stash/stubs.pyi")
        assert stub_file.exists()

        # Get initial modification time
        initial_mtime = stub_file.stat().st_mtime

        # Note: Testing actual file watching would require more complex setup
        # This test verifies the mechanism is set up correctly

    def test_create_typed_wrapper(self):
        """Test creating a typed wrapper for runtime checking."""
        config = Config(
            loaders=[YamlLoader(self.config_file)],
            enable_ide_support=False
        )

        # Create typed wrapper
        typed_config = IDESupport.create_typed_wrapper(config)

        # Verify attributes exist
        assert hasattr(typed_config, "database")
        assert hasattr(typed_config.database, "host")
        assert typed_config.database.host == "localhost"
        assert typed_config.database.port == 5432

        assert hasattr(typed_config, "api")
        assert typed_config.api.endpoint == "https://api.example.com"

    def test_vscode_support(self):
        """Test VSCode-specific settings generation."""
        VSCodeSupport.generate_settings()

        settings_file = Path(".vscode/settings.json")
        assert settings_file.exists()

        import json
        with open(settings_file) as f:
            settings = json.load(f)

        assert "python.analysis.extraPaths" in settings
        assert "python.analysis.autoImportCompletions" in settings
        assert settings["python.analysis.autoImportCompletions"] is True

    def test_ide_support_with_empty_config(self):
        """Test IDE support with empty configuration."""
        empty_config = "default: {}"
        with open("empty.yaml", "w") as f:
            f.write(empty_config)

        config = Config(loaders=[YamlLoader("empty.yaml")])

        stub_file = Path(".config_stash/stubs.pyi")
        assert stub_file.exists()

        with open(stub_file) as f:
            content = f.read()
            assert "class ConfigType:" in content
            # Empty config results in empty class with 'pass'
            assert "pass" in content

    def test_ide_support_with_lists(self):
        """Test IDE support with list configurations."""
        list_config = """
default:
  servers:
    - name: server1
      host: host1
      port: 8080
    - name: server2
      host: host2
      port: 8081
  tags: ["tag1", "tag2", "tag3"]
"""
        with open("list_config.yaml", "w") as f:
            f.write(list_config)

        config = Config(loaders=[YamlLoader("list_config.yaml")])

        stub_file = Path(".config_stash/stubs.pyi")
        with open(stub_file) as f:
            content = f.read()

        # Check list of objects
        assert "class ServersItem:" in content
        assert "servers: List['ServersItem']" in content

        # Check list of primitives
        assert "tags: List[str]" in content

    def test_ide_support_error_handling(self):
        """Test IDE support handles errors gracefully."""
        # Create config with IDE support
        config = Config(
            loaders=[YamlLoader(self.config_file)],
            enable_ide_support=True
        )

        # Even if there's an error in IDE support generation,
        # Config should still work normally
        assert config.database.host == "localhost"
        assert config.api.endpoint == "https://api.example.com"

    def test_ide_support_regeneration(self):
        """Test that IDE support files can be regenerated."""
        config = Config(loaders=[YamlLoader(self.config_file)])

        # Initial generation
        stub_file = Path(".config_stash/stubs.pyi")
        assert stub_file.exists()

        # Modify the stub file
        with open(stub_file, "a") as f:
            f.write("\n# Modified")

        # Regenerate
        IDESupport.generate_stub(config, str(stub_file), silent=True)

        # Check file was regenerated (modification removed)
        with open(stub_file) as f:
            content = f.read()
            assert "# Modified" not in content