"""Bug exposure tests for config-stash.

Each test in this file is designed to FAIL against the current codebase,
demonstrating a specific real bug. Tests are named after the bug they expose.

Once a bug is fixed, the corresponding test should PASS.
"""

import copy
import json
import os
import shutil
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, Mock, call, patch

from config_stash.config import Config
from config_stash.config_merger import ConfigMerger
from config_stash.exceptions import ConfigMergeConflictError


# ---------------------------------------------------------------------------
# Bug 1: Hooks applied TWICE on attribute access
# config.py:482-483 + attribute_accessor.py:51-52
# ---------------------------------------------------------------------------
class TestBug01_DoubleHookApplication(unittest.TestCase):
    """Config.__getattr__ applies hooks, then AttributeAccessor.__getattr__
    also applies hooks. Leaf values get hooks run twice."""

    @patch("config_stash.loaders.yaml_loader.YamlLoader.load")
    def test_hooks_applied_exactly_once(self, mock_yaml_load):
        """Register a counting hook and verify it fires exactly once per access."""
        from config_stash.loaders.yaml_loader import YamlLoader

        yaml_config = {"default": {"port": "8080"}}

        def yaml_side_effect():
            loader.config = yaml_config["default"]
            return yaml_config

        loader = YamlLoader("config.yaml")
        mock_yaml_load.side_effect = yaml_side_effect

        config = Config(
            env="default",
            loaders=[loader],
            dynamic_reloading=False,
            use_env_expander=False,
            use_type_casting=False,
        )

        # Register a non-idempotent global hook that counts invocations.
        # Global hooks receive (value) only — see hook_processor.py:94
        call_count = {"n": 0}

        def counting_hook(value):
            call_count["n"] += 1
            return value

        config.hook_processor.register_global_hook(counting_hook)

        # Access the value once
        _ = config.port

        self.assertEqual(
            call_count["n"],
            1,
            f"Hook was called {call_count['n']} times instead of 1 — "
            "hooks are being applied twice (once in AttributeAccessor, "
            "once in Config.__getattr__)",
        )


# ---------------------------------------------------------------------------
# Bug 2: ConfigMergeConflictError raised with invalid keyword argument
# config_merger.py:44-49 vs exceptions.py:124-132
# ---------------------------------------------------------------------------
class TestBug02_MergeConflictErrorInvalidKwarg(unittest.TestCase):
    """ConfigMerger passes `original_error=e` to ConfigMergeConflictError,
    but that class does not accept that parameter — raises TypeError."""

    def test_merge_error_does_not_raise_typeerror(self):
        """When a merge fails, the error should be ConfigMergeConflictError,
        not TypeError from an invalid keyword argument."""
        # Create configs where merging will raise an exception.
        # Passing a non-dict will cause .items() to fail inside _merge_dicts.
        bad_configs = [
            ({"key": "value"}, "source1"),
            ("not_a_dict", "source2"),  # This will cause .items() to fail
        ]

        # The bug: ConfigMergeConflictError is raised with original_error=e,
        # but that class doesn't accept that kwarg → TypeError masks the real error
        try:
            ConfigMerger.merge_configs(bad_configs, deep_merge=False)
            self.fail("Expected an exception from merging invalid config")
        except TypeError as e:
            if "original_error" in str(e):
                self.fail(
                    f"Got TypeError due to invalid keyword argument: {e}. "
                    "ConfigMergeConflictError.__init__() does not accept "
                    "'original_error' parameter."
                )
            raise  # Re-raise if it's a different TypeError
        except ConfigMergeConflictError:
            pass  # This is the expected behavior after fix


# ---------------------------------------------------------------------------
# Bug 3: Deep merge mutates original config dicts in-place
# config_merger.py:73-89
# ---------------------------------------------------------------------------
class TestBug03_DeepMergeMutatesOriginal(unittest.TestCase):
    """_merge_dicts modifies the base dict in-place. The first config's
    nested dicts are corrupted after merging."""

    def test_original_config_unchanged_after_deep_merge(self):
        """After deep merge, the original config dicts should be unmodified."""
        config1 = {
            "database": {
                "host": "localhost",
                "port": 5432,
            }
        }
        config2 = {
            "database": {
                "host": "production.db",
                "ssl": True,
            }
        }

        # Deep copy to verify later
        config1_before = copy.deepcopy(config1)

        configs = [(config1, "source1"), (config2, "source2")]
        merged = ConfigMerger.merge_configs(configs, deep_merge=True)

        # The merged result should be correct
        self.assertEqual(merged["database"]["host"], "production.db")
        self.assertEqual(merged["database"]["port"], 5432)
        self.assertTrue(merged["database"]["ssl"])

        # Bug: config1 is mutated in-place by _merge_dicts
        self.assertEqual(
            config1,
            config1_before,
            "Original config1 was mutated during deep merge! "
            f"Before: {config1_before}, After: {config1}",
        )


# ---------------------------------------------------------------------------
# Bug 4: dry_run=True in reload() still applies changes without validation
# config.py:576-593
# ---------------------------------------------------------------------------
class TestBug04_DryRunAppliesChangesWithoutValidation(unittest.TestCase):
    """When validation is disabled, dry_run=True is ignored and changes
    are applied anyway."""

    def test_dry_run_does_not_apply_changes_without_validation(self):
        """reload(dry_run=True) should never apply changes, even without validation."""
        temp_dir = tempfile.mkdtemp()
        try:
            config_path = os.path.join(temp_dir, "config.yaml")
            with open(config_path, "w") as f:
                f.write("default:\n  host: original\n")

            from config_stash.loaders.yaml_loader import YamlLoader

            config = Config(
                env="default",
                loaders=[YamlLoader(config_path)],
                dynamic_reloading=False,
                validate_on_load=False,  # No validation
            )

            self.assertEqual(config.host, "original")

            # Modify the file
            with open(config_path, "w") as f:
                f.write("default:\n  host: changed\n")

            # Dry run should NOT apply changes
            config.reload(dry_run=True)

            self.assertEqual(
                config.host,
                "original",
                "dry_run=True applied changes even though it shouldn't have! "
                "The dry_run check is only inside the validation block.",
            )
        finally:
            shutil.rmtree(temp_dir)


# ---------------------------------------------------------------------------
# Bug 5: Crash when self.env is None — prefix.startswith(None)
# config.py:371
# ---------------------------------------------------------------------------
class TestBug05_NoneEnvCrash(unittest.TestCase):
    """When self.env is set to None after init, _track_config_values crashes
    with TypeError: startswith first arg must be str.
    The constructor guards with `env or default`, but the code at line 371
    is still fragile — directly test the method."""

    @patch("config_stash.loaders.yaml_loader.YamlLoader.load")
    def test_track_config_values_with_none_env(self, mock_yaml_load):
        """_track_config_values should handle None env gracefully."""
        from config_stash.loaders.yaml_loader import YamlLoader

        yaml_config = {"default": {"db": {"host": "localhost"}}}
        loader = YamlLoader("config.yaml")

        def yaml_side_effect():
            loader.config = yaml_config["default"]
            return yaml_config

        mock_yaml_load.side_effect = yaml_side_effect

        config = Config(
            env="default",
            loaders=[loader],
            dynamic_reloading=False,
        )

        # Simulate env becoming None (e.g., via direct assignment or subclass)
        config.env = None

        # This should not raise TypeError
        try:
            config._track_config_values(
                {"nested": {"key": "val"}}, "source.yaml", "YamlLoader", "some_prefix"
            )
        except TypeError as e:
            if "startswith" in str(e):
                self.fail(
                    f"_track_config_values crashes with TypeError when self.env=None: {e}. "
                    "prefix.startswith(self.env) fails when self.env is None."
                )
            raise


# ---------------------------------------------------------------------------
# Bug 6: Config files loaded twice during initialization
# config.py:148 (LoaderManager.__init__) and config.py:162
# ---------------------------------------------------------------------------
class TestBug06_ConfigLoadedTwice(unittest.TestCase):
    """LoaderManager.__init__ loads all configs, then Config.__init__
    loads them again via _load_configs_with_tracking."""

    def test_loader_load_called_exactly_once(self):
        """Each loader's load() should be called exactly once during init."""
        mock_loader = MagicMock()
        mock_loader.source = "mock_config.yaml"
        mock_loader.config = {"default": {"key": "value"}}
        mock_loader.load.return_value = {"default": {"key": "value"}}

        config = Config(
            env="default",
            loaders=[mock_loader],
            dynamic_reloading=False,
        )

        load_call_count = mock_loader.load.call_count
        self.assertEqual(
            load_call_count,
            1,
            f"loader.load() was called {load_call_count} times instead of 1. "
            "Config files are being loaded twice during initialization.",
        )


# ---------------------------------------------------------------------------
# Bug 7: FileNotFoundError dead code in JSON/YAML/TOML loaders
# json_loader.py:63-65 — _read_file raises ConfigLoadError, not FileNotFoundError
# ---------------------------------------------------------------------------
class TestBug07_MissingFileReturnsNone(unittest.TestCase):
    """Loaders document that missing files return None, but _read_file
    converts FileNotFoundError to ConfigLoadError before the catch."""

    def test_json_loader_missing_file_returns_none(self):
        """JsonLoader should return None for missing files, not raise."""
        from config_stash.loaders.json_loader import JsonLoader

        loader = JsonLoader("/nonexistent/path/config.json")
        result = loader.load()
        self.assertIsNone(
            result,
            "JsonLoader raised an exception for missing file instead of "
            "returning None. The FileNotFoundError handler is dead code "
            "because _read_file wraps it in ConfigLoadError first.",
        )

    def test_yaml_loader_missing_file_returns_none(self):
        """YamlLoader should return None for missing files, not raise."""
        from config_stash.loaders.yaml_loader import YamlLoader

        loader = YamlLoader("/nonexistent/path/config.yaml")
        result = loader.load()
        self.assertIsNone(
            result,
            "YamlLoader raised an exception for missing file instead of "
            "returning None.",
        )

    def test_toml_loader_missing_file_returns_none(self):
        """TomlLoader should return None for missing files, not raise."""
        from config_stash.loaders.toml_loader import TomlLoader

        loader = TomlLoader("/nonexistent/path/config.toml")
        result = loader.load()
        self.assertIsNone(
            result,
            "TomlLoader raised an exception for missing file instead of "
            "returning None.",
        )


# ---------------------------------------------------------------------------
# Bug 8a: EnvFileLoader doesn't strip inline comments
# Bug 8b: EnvFileLoader processes escape sequences in single-quoted values
# env_file_loader.py:42, 49
# ---------------------------------------------------------------------------
class TestBug08a_EnvFileInlineComments(unittest.TestCase):
    """EnvFileLoader should strip inline comments after values."""

    def test_inline_comments_stripped(self):
        """Values with inline comments should not include the comment."""
        temp_dir = tempfile.mkdtemp()
        try:
            env_path = os.path.join(temp_dir, ".env")
            with open(env_path, "w") as f:
                f.write("HOST=localhost # production server\n")
                f.write("PORT=8080 # default port\n")

            from config_stash.loaders.env_file_loader import EnvFileLoader

            loader = EnvFileLoader(env_path)
            config = loader.load()

            self.assertEqual(
                config["HOST"],
                "localhost",
                f"Inline comment not stripped. Got: '{config['HOST']}' "
                "instead of 'localhost'",
            )
        finally:
            shutil.rmtree(temp_dir)


class TestBug08b_EnvFileSingleQuoteEscapes(unittest.TestCase):
    """Single-quoted values should be treated as literals — no escape processing."""

    def test_single_quoted_values_are_literal(self):
        """Escape sequences inside single quotes should not be processed."""
        temp_dir = tempfile.mkdtemp()
        try:
            env_path = os.path.join(temp_dir, ".env")
            with open(env_path, "w") as f:
                f.write("PATH_VAL='C:\\\\new\\\\test'\n")

            from config_stash.loaders.env_file_loader import EnvFileLoader

            loader = EnvFileLoader(env_path)
            config = loader.load()

            # After stripping single quotes, literal content is C:\\new\\test
            # Bug: the loader then converts \\n to newline
            self.assertNotIn(
                "\n",
                config["PATH_VAL"],
                "Escape sequences were processed inside single-quoted value. "
                "Single-quoted .env values should be treated as literals.",
            )
        finally:
            shutil.rmtree(temp_dir)


# ---------------------------------------------------------------------------
# Bug 9: CLI _parse_override_value treats "0" as False and "1" as True
# cli.py:99-101
# ---------------------------------------------------------------------------
class TestBug09_CliOverrideNumericParsing(unittest.TestCase):
    """The boolean check in _parse_override_value runs before the int check,
    so "0" becomes False and "1" becomes True instead of integers."""

    def test_zero_parsed_as_int_not_bool(self):
        from config_stash.cli import _parse_override_value

        result = _parse_override_value("0")
        # Must use `type() is` because bool is a subclass of int
        self.assertTrue(
            type(result) is int,
            f"_parse_override_value('0') returned {type(result).__name__}({result}) "
            "instead of int(0). The boolean check intercepts '0' before the int check.",
        )
        self.assertEqual(result, 0)

    def test_one_parsed_as_int_not_bool(self):
        from config_stash.cli import _parse_override_value

        result = _parse_override_value("1")
        # Must use `type() is` because bool is a subclass of int
        self.assertTrue(
            type(result) is int,
            f"_parse_override_value('1') returned {type(result).__name__}({result}) "
            "instead of int(1). The boolean check intercepts '1' before the int check.",
        )
        self.assertEqual(result, 1)


# ---------------------------------------------------------------------------
# Bug 10: ConfigVersionManager.rollback() returns mutable reference
# config_versioning.py:234
# ---------------------------------------------------------------------------
class TestBug10_RollbackReturnsMutableReference(unittest.TestCase):
    """rollback() returns the stored config_dict directly. Mutating the
    return value corrupts the version history."""

    def test_rollback_returns_independent_copy(self):
        """Modifying the rollback result should not affect stored version."""
        from config_stash.config_versioning import ConfigVersionManager

        temp_dir = tempfile.mkdtemp()
        try:
            manager = ConfigVersionManager(storage_path=temp_dir)
            original = {"database": {"host": "localhost", "port": 5432}}
            version = manager.save_version(original)

            # Get the rolled-back config
            rolled_back = manager.rollback(version.version_id)

            # Mutate the returned value
            rolled_back["database"]["host"] = "CORRUPTED"

            # Fetch the version again — it should be untouched
            rolled_back2 = manager.rollback(version.version_id)
            self.assertEqual(
                rolled_back2["database"]["host"],
                "localhost",
                "Modifying the rollback result corrupted the stored version! "
                "rollback() returns a mutable reference instead of a copy.",
            )
        finally:
            shutil.rmtree(temp_dir)


# ---------------------------------------------------------------------------
# Bug 11: ConfigComposer.compose() mutates input via pop()
# config_composition.py:77-83
# ---------------------------------------------------------------------------
class TestBug11_ComposeMutatesInput(unittest.TestCase):
    """compose() calls pop() on the input config dict, destroying
    _defaults and _include keys. Second call won't process them."""

    def test_compose_does_not_mutate_input(self):
        """Calling compose() should not modify the input dict."""
        from config_stash.config_composition import ConfigComposer

        composer = ConfigComposer(base_path="/tmp")
        config = {
            "_defaults": [],
            "_include": [],
            "app": {"name": "MyApp"},
        }
        config_before = copy.deepcopy(config)

        composer.compose(config, source="test.yaml")

        self.assertIn(
            "_defaults",
            config,
            "compose() removed '_defaults' from the input dict via pop(). "
            "Input should not be mutated.",
        )
        self.assertIn(
            "_include",
            config,
            "compose() removed '_include' from the input dict via pop(). "
            "Input should not be mutated.",
        )


# ---------------------------------------------------------------------------
# Bug 11b: ConfigComposer._merge_dicts drops ALL underscore-prefixed keys
# config_composition.py:255
# ---------------------------------------------------------------------------
class TestBug11b_UnderscorePrefixedKeysDropped(unittest.TestCase):
    """_merge_dicts skips all keys starting with '_', not just directives."""

    def test_legitimate_underscore_keys_preserved(self):
        """Keys like _internal_port should not be silently dropped."""
        from config_stash.config_composition import ConfigComposer

        composer = ConfigComposer()
        base = {"app": "myapp"}
        new = {
            "_internal_port": 9090,
            "_private_setting": "secret",
            "app": "myapp",
        }

        result = composer._merge_dicts(base, new)

        self.assertIn(
            "_internal_port",
            result,
            "Legitimate key '_internal_port' was silently dropped because "
            "it starts with '_'. Only composition directives should be skipped.",
        )
        self.assertEqual(result["_internal_port"], 9090)


# ---------------------------------------------------------------------------
# Bug 12: ConfigFileWatcher.stop() crashes if start() was never called
# config_watcher.py:38-40
# ---------------------------------------------------------------------------
class TestBug12_WatcherStopWithoutStart(unittest.TestCase):
    """Calling stop() without start() raises RuntimeError because
    observer.join() is called on an un-started thread."""

    def test_stop_without_start_does_not_crash(self):
        """stop() should be safe to call even if start() was never called."""
        from config_stash.config_watcher import ConfigFileWatcher

        mock_config = MagicMock()
        mock_config.get_watched_files.return_value = []

        watcher = ConfigFileWatcher(mock_config)

        # This should not raise RuntimeError
        try:
            watcher.stop()
        except RuntimeError as e:
            self.fail(
                f"ConfigFileWatcher.stop() raised RuntimeError when called "
                f"without start(): {e}"
            )


# ---------------------------------------------------------------------------
# Bug 13: EnvFileLoader negative integers parsed as floats
# env_file_loader.py:57 — isdigit() returns False for "-1"
# ---------------------------------------------------------------------------
class TestBug13_NegativeIntegerParsing(unittest.TestCase):
    """str.isdigit() returns False for negative numbers, so they fall
    through to float() parsing."""

    def test_negative_integer_parsed_as_int(self):
        """Negative integers in .env files should be parsed as int, not float."""
        temp_dir = tempfile.mkdtemp()
        try:
            env_path = os.path.join(temp_dir, ".env")
            with open(env_path, "w") as f:
                f.write("RETRIES=-1\n")
                f.write("OFFSET=-42\n")

            from config_stash.loaders.env_file_loader import EnvFileLoader

            loader = EnvFileLoader(env_path)
            config = loader.load()

            self.assertIsInstance(
                config["RETRIES"],
                int,
                f"RETRIES=-1 was parsed as {type(config['RETRIES']).__name__} "
                f"({config['RETRIES']}) instead of int. "
                "isdigit() returns False for negative numbers.",
            )
            self.assertEqual(config["RETRIES"], -1)
        finally:
            shutil.rmtree(temp_dir)


# ---------------------------------------------------------------------------
# Bug 14: Version IDs based solely on content hash — metadata overwritten
# config_versioning.py:89-136
# ---------------------------------------------------------------------------
class TestBug14_VersionMetadataOverwritten(unittest.TestCase):
    """Saving the same config with different metadata silently overwrites
    the earlier version's metadata because version ID = content hash."""

    def test_same_config_different_metadata_preserved(self):
        """Two saves with same config but different metadata should either
        create distinct versions or at minimum preserve both metadata sets."""
        from config_stash.config_versioning import ConfigVersionManager

        temp_dir = tempfile.mkdtemp()
        try:
            manager = ConfigVersionManager(storage_path=temp_dir)
            config = {"database": {"host": "localhost"}}

            v1 = manager.save_version(
                config, metadata={"author": "alice", "message": "initial"}
            )
            time.sleep(0.01)  # Ensure different timestamp
            v2 = manager.save_version(
                config, metadata={"author": "bob", "message": "reviewed"}
            )

            # Both versions have the same ID (content hash) — that's the root issue
            # At minimum, the first version's metadata should still be retrievable
            retrieved = manager.get_version(v1.version_id)

            # The bug: v2 overwrites v1's metadata
            self.assertEqual(
                retrieved.metadata["author"],
                "alice",
                f"First version's metadata was overwritten. "
                f"Expected author='alice', got author='{retrieved.metadata['author']}'. "
                "Version ID is a pure content hash, so same config = same ID = overwrite.",
            )
        finally:
            shutil.rmtree(temp_dir)


# ===========================================================================
# BATCH 2: Remaining bugs from the deep review
# ===========================================================================


# ---------------------------------------------------------------------------
# Bug 15: EnvSecretStore leaks environment variable names in error messages
# env_secret_store.py:136
# ---------------------------------------------------------------------------
class TestBug15_EnvSecretStoreLeaksEnvVarNames(unittest.TestCase):
    """Error messages should NOT include os.environ.keys() — information disclosure."""

    def test_error_message_does_not_leak_env_vars(self):
        from config_stash.secret_stores.providers.env_secret_store import EnvSecretStore

        store = EnvSecretStore()
        try:
            store.get_secret("nonexistent/secret/key")
            self.fail("Expected SecretNotFoundError")
        except Exception as e:
            error_msg = str(e)
            # The error should NOT contain a list of environment variable names
            self.assertNotIn(
                "Available variables:",
                error_msg,
                "Error message leaks environment variable names — "
                "information disclosure vulnerability.",
            )


# ---------------------------------------------------------------------------
# Bug 16: IniLoader doesn't inherit from Loader base class
# ini_loader.py:8
# ---------------------------------------------------------------------------
class TestBug16_IniLoaderNotALoader(unittest.TestCase):
    """IniLoader should be recognized as a Loader instance."""

    def test_ini_loader_is_instance_of_loader(self):
        from config_stash.loaders.ini_loader import IniLoader
        from config_stash.loaders.loader import Loader

        loader = IniLoader("config.ini")
        self.assertIsInstance(
            loader,
            Loader,
            "IniLoader does not inherit from Loader base class. "
            "isinstance(loader, Loader) is False.",
        )


# ---------------------------------------------------------------------------
# Bug 17: IniLoader negative integers parsed as floats (same as env_file)
# ini_loader.py:42 — isdigit() returns False for "-1"
# ---------------------------------------------------------------------------
class TestBug17_IniLoaderNegativeIntegers(unittest.TestCase):
    """IniLoader uses isdigit() which fails for negative numbers."""

    def test_negative_integer_parsed_as_int(self):
        from config_stash.loaders.ini_loader import IniLoader

        temp_dir = tempfile.mkdtemp()
        try:
            ini_path = os.path.join(temp_dir, "config.ini")
            with open(ini_path, "w") as f:
                f.write("[settings]\nretries = -5\noffset = -100\n")

            loader = IniLoader(ini_path)
            config = loader.load()

            self.assertIsInstance(
                config["settings"]["retries"],
                int,
                f"retries=-5 was parsed as {type(config['settings']['retries']).__name__} "
                f"instead of int.",
            )
            self.assertEqual(config["settings"]["retries"], -5)
        finally:
            shutil.rmtree(temp_dir)


# ---------------------------------------------------------------------------
# Bug 18: IniLoader silently ignores file read permission errors
# ini_loader.py:30 — parser.read() doesn't check return value
# ---------------------------------------------------------------------------
class TestBug18_IniLoaderSilentPermissionError(unittest.TestCase):
    """parser.read() silently ignores unreadable files — returns empty config."""

    def test_unreadable_file_returns_empty_or_raises(self):
        """An unreadable INI file should raise or return None, not empty dict."""
        from config_stash.loaders.ini_loader import IniLoader

        temp_dir = tempfile.mkdtemp()
        try:
            ini_path = os.path.join(temp_dir, "config.ini")
            with open(ini_path, "w") as f:
                f.write("[database]\nhost = localhost\nport = 5432\n")

            # Remove read permissions
            os.chmod(ini_path, 0o000)

            loader = IniLoader(ini_path)
            config = loader.load()

            # Bug: parser.read() silently fails, returning {}
            # It should either raise or return None
            self.assertIsNone(
                config,
                f"IniLoader returned {config} for unreadable file instead of None. "
                "parser.read() silently ignores permission errors.",
            )
        finally:
            os.chmod(os.path.join(temp_dir, "config.ini"), 0o644)
            shutil.rmtree(temp_dir)


# ---------------------------------------------------------------------------
# Bug 19: GitLoader breaks for .git URLs
# remote_loader.py:219-228
# ---------------------------------------------------------------------------
class TestBug19_GitLoaderDotGitUrls(unittest.TestCase):
    """GitLoader doesn't strip .git suffix from repo URLs."""

    def test_github_url_with_git_suffix(self):
        from config_stash.loaders.remote_loader import GitLoader

        loader = GitLoader(
            "https://github.com/org/repo.git",
            file_path="config.yaml",
        )

        # Intercept HTTPLoader to capture the raw_url
        with patch("config_stash.loaders.remote_loader.HTTPLoader") as mock_http:
            mock_http.return_value.load.return_value = {"key": "value"}
            try:
                loader.load()
            except Exception:
                pass

            if mock_http.called:
                raw_url = mock_http.call_args[0][0]
                # Check the path portion after the domain, not the full URL
                # (githubusercontent contains "git")
                path_part = raw_url.split(".com/", 1)[-1]
                self.assertNotIn(
                    ".git",
                    path_part,
                    f"GitLoader did not strip .git suffix from raw URL path: '{path_part}'.",
                )


# ---------------------------------------------------------------------------
# Bug 20: GitLoader uses wrong auth header for GitLab
# remote_loader.py:234-235
# ---------------------------------------------------------------------------
class TestBug20_GitLoaderGitLabAuth(unittest.TestCase):
    """GitLab uses PRIVATE-TOKEN header, not GitHub's 'token' prefix."""

    def test_gitlab_uses_correct_auth_header(self):
        from config_stash.loaders.remote_loader import GitLoader

        loader = GitLoader(
            "https://gitlab.com/org/repo",
            file_path="config.yaml",
            token="my-token",
        )

        # Verify the loader constructs the correct auth for GitLab
        # We need to intercept the HTTPLoader creation
        with patch("config_stash.loaders.remote_loader.HTTPLoader") as mock_http:
            mock_http.return_value.load.return_value = {"key": "value"}
            try:
                loader.load()
            except Exception:
                pass

            if mock_http.called:
                call_kwargs = mock_http.call_args
                headers = call_kwargs[1].get("headers", {}) if call_kwargs[1] else {}
                if not headers and len(call_kwargs[0]) > 1:
                    headers = call_kwargs[0][1]

                auth_value = headers.get("Authorization", "")
                self.assertNotIn(
                    "token ",
                    auth_value,
                    f"GitLab auth uses GitHub-style 'token' prefix: '{auth_value}'. "
                    "Should use 'Bearer' or PRIVATE-TOKEN header.",
                )


# ---------------------------------------------------------------------------
# Bug 21: AzureBlobLoader produces https://None.blob.core.windows.net
# remote_loader.py:300-307
# ---------------------------------------------------------------------------
class TestBug21_AzureBlobLoaderNoneAccountName(unittest.TestCase):
    """When account_name is None, the URL becomes https://None.blob.core.windows.net."""

    def test_none_account_name_validated_at_init_or_load(self):
        """AzureBlobLoader should validate account_name is not None before building URL."""
        with open("src/config_stash/loaders/remote_loader.py", "r") as f:
            source = f.read()

        # Check that there's a guard for None account_name before the
        # DefaultAzureCredential fallback path
        self.assertIn(
            "not self.account_name",
            source,
            "AzureBlobLoader DefaultAzureCredential path uses self.account_name "
            "in URL without checking for None. Would produce https://None.blob.core.windows.net",
        )


# ---------------------------------------------------------------------------
# Bug 22: ConfigDiff.to_dict() drops legitimate None values
# config_diff.py:89-92
# ---------------------------------------------------------------------------
class TestBug22_ConfigDiffDropsNoneValues(unittest.TestCase):
    """to_dict() skips old_value/new_value when they are None,
    even if that's the actual value (e.g., key modified TO None)."""

    def test_modified_to_none_includes_new_value(self):
        from config_stash.config_diff import ConfigDiff, DiffType

        diff = ConfigDiff(
            key="setting",
            diff_type=DiffType.MODIFIED,
            old_value="something",
            new_value=None,
        )
        result = diff.to_dict()

        self.assertIn(
            "new_value",
            result,
            "to_dict() dropped 'new_value' because it was None. "
            "But None is a valid value for MODIFIED diffs.",
        )
        self.assertIsNone(result["new_value"])

    def test_removed_key_with_none_value(self):
        from config_stash.config_diff import ConfigDiff, DiffType

        diff = ConfigDiff(
            key="setting",
            diff_type=DiffType.REMOVED,
            old_value=None,
            new_value=None,
        )
        result = diff.to_dict()

        self.assertIn(
            "old_value",
            result,
            "to_dict() dropped 'old_value' for REMOVED diff because it was None.",
        )


# ---------------------------------------------------------------------------
# Bug 23: diff_summary double-counts nested diffs
# config_diff.py:185-199
# ---------------------------------------------------------------------------
class TestBug23_DiffSummaryDoubleCount(unittest.TestCase):
    """total = len(diffs) counts only top-level, but added/removed/modified
    are counted recursively. The sum exceeds total."""

    def test_summary_total_equals_category_sum(self):
        from config_stash.config_diff import ConfigDiff, ConfigDiffer, DiffType

        # Create a parent MODIFIED diff with nested child diffs
        parent = ConfigDiff(key="database", diff_type=DiffType.MODIFIED)
        parent.nested_diffs = [
            ConfigDiff(
                key="host",
                diff_type=DiffType.MODIFIED,
                old_value="old",
                new_value="new",
            ),
            ConfigDiff(key="ssl", diff_type=DiffType.ADDED, new_value=True),
        ]

        summary = ConfigDiffer.diff_summary([parent])

        category_sum = summary["added"] + summary["removed"] + summary["modified"]
        self.assertEqual(
            summary["total"],
            category_sum,
            f"total={summary['total']} but added+removed+modified={category_sum}. "
            "Nested diffs are counted in categories but not in total.",
        )


# ---------------------------------------------------------------------------
# Bug 24: asyncio.get_event_loop() deprecated in Python 3.10+
# async_config.py:68 and 300
# ---------------------------------------------------------------------------
class TestBug24_AsyncioDeprecatedGetEventLoop(unittest.TestCase):
    """asyncio.get_event_loop() should be asyncio.get_running_loop() in async context."""

    def test_async_yaml_loader_uses_get_running_loop(self):
        """Verify AsyncYamlLoader.load() uses get_running_loop(), not get_event_loop()."""
        import ast

        with open("src/config_stash/async_config.py", "r") as f:
            source = f.read()

        tree = ast.parse(source)

        # Find all calls to asyncio.get_event_loop() inside async functions
        deprecated_calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        func = child.func
                        if (
                            isinstance(func, ast.Attribute)
                            and func.attr == "get_event_loop"
                            and isinstance(func.value, ast.Name)
                            and func.value.id == "asyncio"
                        ):
                            deprecated_calls.append(
                                f"line {child.lineno}: asyncio.get_event_loop() "
                                f"in async def {node.name}"
                            )

        self.assertEqual(
            len(deprecated_calls),
            0,
            f"Found deprecated asyncio.get_event_loop() in async functions: "
            f"{deprecated_calls}. Use asyncio.get_running_loop() instead.",
        )


# ---------------------------------------------------------------------------
# Bug 25: AsyncConfig Pydantic detection is fragile
# async_config.py:309-311
# ---------------------------------------------------------------------------
class TestBug25_AsyncConfigPydanticDetection(unittest.TestCase):
    """String-matching 'BaseModel' in __bases__ fails for grandchild models."""

    def test_pydantic_grandchild_model_detected(self):
        """A model inheriting from another Pydantic model should still be detected."""
        try:
            from pydantic import BaseModel
        except ImportError:
            self.skipTest("pydantic not installed")

        from config_stash.async_config import AsyncConfig

        class ParentModel(BaseModel):
            name: str = "test"

        class ChildModel(ParentModel):
            age: int = 25

        # ChildModel.__bases__ is (ParentModel,), not (BaseModel,)
        # The fragile check: any("BaseModel" in str(base) for base in schema.__bases__)
        # will fail because str(ParentModel) doesn't contain "BaseModel"
        config = AsyncConfig.__new__(AsyncConfig)
        config._config = {"name": "wrong", "age": -1}

        # _validate_sync should recognize ChildModel as Pydantic and validate it
        # If detection fails, it falls through to bool(config) which always returns True
        # We can verify by passing INVALID data — only real Pydantic validation will catch it
        result = config._validate_sync({"name": 123}, ChildModel)  # name should be str

        # If Pydantic is properly detected, this should return False (validation fail)
        # If not detected, it returns bool({"name": 123}) == True
        self.assertFalse(
            result,
            "AsyncConfig._validate_sync returned True for invalid data with a "
            "Pydantic grandchild model — it failed to detect the model as Pydantic "
            "because string-matching 'BaseModel' in __bases__ is fragile.",
        )


# Bug 26 (AdvancedConfigMerger shallow copy) — verified as not triggering
# with current strategy implementations. Removed.


# ---------------------------------------------------------------------------
# Bug 27: Config.schema attribute shadows schema() method
# config.py:139 vs config.py:812
# ---------------------------------------------------------------------------
class TestBug27_SchemaMethodShadowed(unittest.TestCase):
    """self.schema = schema in __init__ shadows the schema() method."""

    @patch("config_stash.loaders.yaml_loader.YamlLoader.load")
    def test_schema_method_callable_after_init(self, mock_yaml_load):
        from config_stash.loaders.yaml_loader import YamlLoader

        yaml_config = {"default": {"host": "localhost"}}
        loader = YamlLoader("config.yaml")

        def yaml_side_effect():
            loader.config = yaml_config["default"]
            return yaml_config

        mock_yaml_load.side_effect = yaml_side_effect

        # Pass a schema dict to Config
        schema = {"type": "object", "properties": {"host": {"type": "string"}}}
        config = Config(
            env="default",
            loaders=[loader],
            dynamic_reloading=False,
            schema=schema,
        )

        # config.schema should be callable as a method
        self.assertTrue(
            callable(getattr(config, "schema", None))
            or hasattr(type(config), "schema")
            and callable(type(config).schema),
            "config.schema is not callable — the schema attribute shadows the "
            "schema() method.",
        )

        # Try calling it
        try:
            result = config.schema()
        except TypeError as e:
            if "not callable" in str(e) or "argument" in str(e):
                self.fail(
                    f"config.schema() raises TypeError: {e}. "
                    "The instance attribute shadows the method."
                )
            raise


# ---------------------------------------------------------------------------
# Bug 28: SchemaValidator.validate_with_defaults() mutates input dict
# schema_validator.py:59-78
# ---------------------------------------------------------------------------
class TestBug28_SchemaValidatorMutatesInput(unittest.TestCase):
    """validate_with_defaults() inserts defaults into the caller's dict."""

    def test_validate_with_defaults_does_not_mutate_input(self):
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
        config = {"name": "mydb"}
        config_before = config.copy()

        result = validator.validate_with_defaults(config)

        # Result should have defaults applied
        self.assertEqual(result["host"], "localhost")
        self.assertEqual(result["port"], 5432)

        # But the original input should NOT be mutated
        self.assertEqual(
            config,
            config_before,
            f"validate_with_defaults() mutated the input dict. "
            f"Before: {config_before}, After: {config}",
        )


# ---------------------------------------------------------------------------
# Bug 29: OIDC callback server socket never closed
# vault_auth/oidc.py:286-303
# ---------------------------------------------------------------------------
class TestBug29_OidcServerNotClosed(unittest.TestCase):
    """The HTTPServer created for OIDC callback is never closed."""

    def test_oidc_auth_code_contains_server_close(self):
        """Check that the OIDC authenticate method calls server_close() or
        uses a context manager to properly clean up the HTTP server."""
        import ast

        with open("src/config_stash/secret_stores/vault_auth/oidc.py", "r") as f:
            source = f.read()

        # Check if server_close() or server.close() appears in the source
        has_cleanup = (
            "server_close()" in source
            or "server.close()" in source
            or "with HTTPServer" in source
            or "finally:" in source
            and "server" in source
        )

        self.assertTrue(
            has_cleanup,
            "OIDC callback HTTPServer is never closed (no server_close() call). "
            "The socket remains bound, causing address-in-use on retry.",
        )


# ---------------------------------------------------------------------------
# Bug 30: HashiCorpVault.__init__ double-wraps exceptions
# hashicorp_vault.py:135-157
# ---------------------------------------------------------------------------
class TestBug30_VaultDoubleWrapsExceptions(unittest.TestCase):
    """The except block catches SecretAccessError and wraps it again."""

    def test_vault_init_error_not_double_wrapped(self):
        """Check that SecretAccessError is re-raised before the catch-all
        except Exception handler to prevent double-wrapping."""
        with open(
            "src/config_stash/secret_stores/providers/hashicorp_vault.py", "r"
        ) as f:
            source = f.read()

        # The fix should have a handler that re-raises SecretAccessError
        # before the catch-all 'except Exception' handler
        has_reraise_guard = (
            "except (SecretAccessError" in source
            or "except SecretAccessError" in source
        )

        self.assertTrue(
            has_reraise_guard,
            "HashiCorpVault.__init__ has 'except Exception' that catches and "
            "re-wraps SecretAccessError. Should have 'except SecretAccessError: raise' "
            "before the catch-all.",
        )


# ---------------------------------------------------------------------------
# Bug 31: SchemaValidator.validate_with_defaults() only applies top-level defaults
# schema_validator.py:72-76
# ---------------------------------------------------------------------------
class TestBug31_SchemaValidatorNestedDefaults(unittest.TestCase):
    """validate_with_defaults() only iterates top-level schema properties."""

    def test_nested_defaults_applied(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed")

        from config_stash.validators.schema_validator import SchemaValidator

        schema = {
            "type": "object",
            "properties": {
                "database": {
                    "type": "object",
                    "properties": {
                        "host": {"type": "string", "default": "localhost"},
                        "port": {"type": "integer", "default": 5432},
                    },
                },
            },
        }

        validator = SchemaValidator(schema)
        config = {"database": {}}

        result = validator.validate_with_defaults(config)

        self.assertEqual(
            result["database"].get("host"),
            "localhost",
            "validate_with_defaults() did not apply nested default for 'database.host'. "
            "It only processes top-level properties.",
        )


# ===========================================================================
# BATCH 3: Post-fix deep review — new logical bugs
# ===========================================================================


# ---------------------------------------------------------------------------
# Bug 32: reload(dry_run=True) irreversibly corrupts self.configs/merged_config
# config.py:548-564 — mutated before dry_run check
# ---------------------------------------------------------------------------
class TestBug32_DryRunCorruptsInternalState(unittest.TestCase):
    """dry_run mutates self.configs and self.merged_config before returning."""

    def test_dry_run_does_not_mutate_configs_or_merged_config(self):
        temp_dir = tempfile.mkdtemp()
        try:
            config_path = os.path.join(temp_dir, "config.yaml")
            with open(config_path, "w") as f:
                f.write("default:\n  host: original\n")

            from config_stash.loaders.yaml_loader import YamlLoader

            config = Config(
                env="default",
                loaders=[YamlLoader(config_path)],
                dynamic_reloading=False,
                validate_on_load=False,
            )

            # Capture state before
            merged_before = copy.deepcopy(config.merged_config)

            # Change the file
            with open(config_path, "w") as f:
                f.write("default:\n  host: changed\n")

            # Dry run
            config.reload(dry_run=True)

            # merged_config should NOT have changed
            self.assertEqual(
                config.merged_config,
                merged_before,
                "reload(dry_run=True) mutated self.merged_config. "
                "Internal state is corrupted after a dry run.",
            )
        finally:
            shutil.rmtree(temp_dir)


# ---------------------------------------------------------------------------
# Bug 33: EnvironmentHandler._merge_dicts mutates nested default dicts
# environment_handler.py:50-56
# ---------------------------------------------------------------------------
class TestBug33_EnvironmentHandlerMutatesDefaults(unittest.TestCase):
    """_merge_dicts mutates nested dicts from the original 'default' section."""

    def test_get_env_config_does_not_mutate_defaults(self):
        from config_stash.environment_handler import EnvironmentHandler

        config = {
            "default": {
                "database": {"host": "localhost", "port": 5432},
            },
            "production": {
                "database": {"host": "prod.db.com", "ssl": True},
            },
        }

        default_before = copy.deepcopy(config["default"])

        handler = EnvironmentHandler("production", config)
        result = handler.get_env_config()

        # Result should be correct
        self.assertEqual(result["database"]["host"], "prod.db.com")
        self.assertTrue(result["database"]["ssl"])

        # But the original defaults should NOT be mutated
        self.assertEqual(
            config["default"],
            default_before,
            f"EnvironmentHandler mutated the original 'default' config. "
            f"Before: {default_before}, After: {config['default']}",
        )


# ---------------------------------------------------------------------------
# Bug 34: EnvironmentLoader.load() never resets self.config
# environment_loader.py:52-62
# ---------------------------------------------------------------------------
class TestBug34_EnvironmentLoaderStaleKeys(unittest.TestCase):
    """load() accumulates into self.config — removed env vars persist."""

    def test_removed_env_var_not_in_reload(self):
        from config_stash.loaders.environment_loader import EnvironmentLoader

        loader = EnvironmentLoader("TESTCFG")

        # First load with two env vars
        with patch.dict(
            os.environ,
            {
                "TESTCFG_HOST": "localhost",
                "TESTCFG_PORT": "8080",
            },
            clear=False,
        ):
            result1 = loader.load()
            self.assertEqual(result1["host"], "localhost")
            self.assertEqual(result1["port"], 8080)

        # Second load with one env var removed
        env = os.environ.copy()
        env.pop("TESTCFG_PORT", None)
        env.pop("TESTCFG_HOST", None)
        env["TESTCFG_HOST"] = "newhost"

        with patch.dict(os.environ, env, clear=True):
            result2 = loader.load()
            self.assertNotIn(
                "port",
                result2,
                "Removed env var 'TESTCFG_PORT' still present after reload. "
                "EnvironmentLoader.load() never resets self.config.",
            )


# ---------------------------------------------------------------------------
# Bug 35: EnvironmentLoader negative integers parsed as floats
# environment_loader.py:92 — isdigit()
# ---------------------------------------------------------------------------
class TestBug35_EnvironmentLoaderNegativeIntegers(unittest.TestCase):
    """isdigit() returns False for negative numbers."""

    def test_negative_env_var_parsed_as_int(self):
        from config_stash.loaders.environment_loader import EnvironmentLoader

        loader = EnvironmentLoader("NEGTEST")

        with patch.dict(os.environ, {"NEGTEST_RETRIES": "-3"}, clear=False):
            config = loader.load()
            self.assertIsInstance(
                config["retries"],
                int,
                f"NEGTEST_RETRIES=-3 was parsed as {type(config['retries']).__name__}. "
                "isdigit() returns False for negative numbers.",
            )
            self.assertEqual(config["retries"], -3)


# ---------------------------------------------------------------------------
# Bug 36: EnvFileLoader doesn't inherit from Loader
# env_file_loader.py:8
# ---------------------------------------------------------------------------
class TestBug36_EnvFileLoaderNotALoader(unittest.TestCase):
    """EnvFileLoader should be recognized as a Loader instance."""

    def test_env_file_loader_is_instance_of_loader(self):
        from config_stash.loaders.env_file_loader import EnvFileLoader
        from config_stash.loaders.loader import Loader

        loader = EnvFileLoader(".env")
        self.assertIsInstance(
            loader,
            Loader,
            "EnvFileLoader does not inherit from Loader base class.",
        )


# ---------------------------------------------------------------------------
# Bug 37: Config.set() doesn't update merged_config
# config.py:938-1004
# ---------------------------------------------------------------------------
class TestBug37_SetDoesNotUpdateMergedConfig(unittest.TestCase):
    """set() modifies env_config but not merged_config."""

    @patch("config_stash.loaders.yaml_loader.YamlLoader.load")
    def test_set_updates_merged_config(self, mock_yaml_load):
        from config_stash.loaders.yaml_loader import YamlLoader

        yaml_config = {"default": {"host": "localhost", "port": 5432}}
        loader = YamlLoader("config.yaml")

        def side_effect():
            loader.config = yaml_config["default"]
            return yaml_config

        mock_yaml_load.side_effect = side_effect

        config = Config(
            env="default",
            loaders=[loader],
            dynamic_reloading=False,
        )

        config.set("host", "newhost")

        # env_config should be updated
        self.assertEqual(config.env_config.get("host"), "newhost")

        # merged_config should ALSO reflect the change
        # (it's used as baseline for subsequent reloads)
        self.assertIn(
            "newhost",
            str(config.merged_config),
            "Config.set() did not update merged_config. "
            "Internal state is inconsistent.",
        )


# ---------------------------------------------------------------------------
# Bug 38: ConfigEventEmitter.on() breaks decorator pattern
# observability.py:292-305
# ---------------------------------------------------------------------------
class TestBug38_EventEmitterOnReturnsNone(unittest.TestCase):
    """on() returns None, making decorated function unusable."""

    def test_on_returns_callback_for_decorator_usage(self):
        from config_stash.observability import ConfigEventEmitter

        emitter = ConfigEventEmitter()

        def my_handler(*args):
            pass

        result = emitter.on("reload", my_handler)

        # on() should return the callback so it works as a decorator
        self.assertIs(
            result,
            my_handler,
            f"emitter.on() returned {result} instead of the callback. "
            "This breaks @emitter.on('event') decorator usage.",
        )


# ---------------------------------------------------------------------------
# Bug 39: YamlLoader returns None for empty YAML files
# yaml_loader.py:64
# ---------------------------------------------------------------------------
class TestBug39_YamlLoaderEmptyFileReturnsNone(unittest.TestCase):
    """yaml.safe_load('') returns None, violating Dict contract."""

    def test_empty_yaml_returns_empty_dict(self):
        from config_stash.loaders.yaml_loader import YamlLoader

        temp_dir = tempfile.mkdtemp()
        try:
            yaml_path = os.path.join(temp_dir, "empty.yaml")
            with open(yaml_path, "w") as f:
                f.write("")  # Empty file

            loader = YamlLoader(yaml_path)
            result = loader.load()

            self.assertIsNotNone(
                result,
                "YamlLoader returned None for an empty file. "
                "Should return {} (empty dict).",
            )
            self.assertIsInstance(result, dict)
        finally:
            shutil.rmtree(temp_dir)


# ---------------------------------------------------------------------------
# Bug 40: HTTPLoader doesn't catch parse errors
# remote_loader.py:71-107
# ---------------------------------------------------------------------------
class TestBug40_HTTPLoaderParseError(unittest.TestCase):
    """JSON/YAML/TOML parse errors propagate unhandled."""

    def test_malformed_json_response_wrapped_in_config_error(self):
        try:
            import requests
        except ImportError:
            self.skipTest("requests not installed")

        from config_stash.exceptions import ConfigFormatError, ConfigLoadError
        from config_stash.loaders.remote_loader import HTTPLoader

        loader = HTTPLoader("https://example.com/config.json")

        # Mock a response with invalid JSON
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status.return_value = None

        with patch("requests.get", return_value=mock_response):
            try:
                loader.load()
                self.fail("Expected an exception for malformed JSON")
            except (ConfigLoadError, ConfigFormatError):
                pass  # Expected — properly wrapped
            except (ValueError, Exception) as e:
                if "Invalid JSON" in str(e):
                    self.fail(
                        f"HTTPLoader let parse error propagate unhandled: {type(e).__name__}: {e}. "
                        "Should wrap in ConfigLoadError or ConfigFormatError.",
                    )


# ---------------------------------------------------------------------------
# Bug 41: list_versions() never re-reads disk after first use
# config_versioning.py:188-189
# ---------------------------------------------------------------------------
class TestBug41_ListVersionsStaleCache(unittest.TestCase):
    """Once any version is in memory, disk is never re-scanned."""

    def test_list_versions_picks_up_new_disk_versions(self):
        from config_stash.config_versioning import ConfigVersion, ConfigVersionManager

        temp_dir = tempfile.mkdtemp()
        try:
            manager = ConfigVersionManager(storage_path=temp_dir)

            # Save one version
            v1 = manager.save_version({"key": "value1"})

            # Simulate another process writing a version to disk
            import json as json_mod

            fake_version = ConfigVersion(
                version_id="external_v2",
                config_dict={"key": "value2"},
                metadata={"author": "other_process"},
            )
            with open(os.path.join(temp_dir, "external_v2.json"), "w") as f:
                json_mod.dump(fake_version.to_dict(), f)

            # list_versions should pick up the external version
            versions = manager.list_versions()
            version_ids = [v.version_id for v in versions]

            self.assertIn(
                "external_v2",
                version_ids,
                f"list_versions() did not pick up externally-written version. "
                f"Found: {version_ids}. "
                "Once _versions is non-empty, disk is never re-scanned.",
            )
        finally:
            shutil.rmtree(temp_dir)


# ---------------------------------------------------------------------------
# Bug 42: EnvFileLoader crashes on conflicting scalar/dotted keys
# env_file_loader.py:75-82
# ---------------------------------------------------------------------------
class TestBug42_EnvFileLoaderScalarDottedConflict(unittest.TestCase):
    """Setting db=X then db.host=Y crashes with TypeError."""

    def test_scalar_then_dotted_key_does_not_crash(self):
        from config_stash.loaders.env_file_loader import EnvFileLoader

        temp_dir = tempfile.mkdtemp()
        try:
            env_path = os.path.join(temp_dir, ".env")
            with open(env_path, "w") as f:
                f.write("db=postgres\ndb.host=localhost\n")

            loader = EnvFileLoader(env_path)
            try:
                config = loader.load()
                # The dotted key should win (override scalar with dict)
                self.assertIsInstance(config["db"], dict)
            except TypeError as e:
                self.fail(
                    f"EnvFileLoader crashed on conflicting scalar/dotted keys: {e}. "
                    "A scalar 'db' followed by 'db.host' should promote to dict.",
                )
        finally:
            shutil.rmtree(temp_dir)


# ---------------------------------------------------------------------------
# Bug 43: AsyncConfig.load() silently swallows all loader failures
# async_config.py:239-242
# ---------------------------------------------------------------------------
class TestBug43_AsyncConfigSilentFailure(unittest.TestCase):
    """If ALL loaders fail, caller gets empty config with no error."""

    def test_all_loaders_fail_raises_error(self):
        import asyncio

        from config_stash.async_config import AsyncConfig, AsyncLoader
        from config_stash.exceptions import ConfigLoadError

        class FailingLoader(AsyncLoader):
            async def load(self):
                raise ConfigLoadError("test failure", source="test")

        async def run():
            config = AsyncConfig(loaders=[FailingLoader("test")])
            await config.load()

        # Should raise ConfigLoadError when ALL loaders fail
        with self.assertRaises(ConfigLoadError):
            asyncio.run(run())


# ---------------------------------------------------------------------------
# Bug 44: ConfigComposer._loaded_files cleanup enables duplicate inclusion
# config_composition.py:210,243-244
# ---------------------------------------------------------------------------
class TestBug44_ComposerDuplicateInclusion(unittest.TestCase):
    """Files included by multiple parents get loaded/merged twice."""

    def test_shared_include_loaded_only_once(self):
        from config_stash.config_composition import ConfigComposer

        temp_dir = tempfile.mkdtemp()
        try:
            # Create shared.yaml
            with open(os.path.join(temp_dir, "shared.yaml"), "w") as f:
                f.write("shared_key: shared_value\n")

            # Create b.yaml (includes shared)
            with open(os.path.join(temp_dir, "b.yaml"), "w") as f:
                f.write("_include:\n  - shared.yaml\nb_key: b_value\n")

            # Create c.yaml (also includes shared)
            with open(os.path.join(temp_dir, "c.yaml"), "w") as f:
                f.write("_include:\n  - shared.yaml\nc_key: c_value\n")

            # Track load calls
            load_count = {"n": 0}
            composer = ConfigComposer(base_path=temp_dir)
            original_load = composer._load_include

            def counting_load(file_path, depth):
                if "shared.yaml" in str(file_path):
                    load_count["n"] += 1
                return original_load(file_path, depth)

            composer._load_include = counting_load

            config = {
                "_include": ["b.yaml", "c.yaml"],
                "main_key": "main_value",
            }
            composer.compose(config, source=os.path.join(temp_dir, "main.yaml"))

            self.assertEqual(
                load_count["n"],
                1,
                f"shared.yaml was loaded {load_count['n']} times instead of 1. "
                "_loaded_files cleanup enables duplicate inclusion.",
            )
        finally:
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    unittest.main()
