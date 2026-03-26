"""Tests for the `cs` short alias package.

Verifies that `from cs import X` works identically to `from config_stash import X`.
"""

import unittest


class TestCsAlias(unittest.TestCase):
    """Verify cs.* imports resolve to the same objects as config_stash.*"""

    def test_top_level_imports(self):
        from config_stash import Config as CS_Config
        from config_stash import ConfigBuilder as CS_Builder
        from cs import Config, ConfigBuilder

        self.assertIs(Config, CS_Config)
        self.assertIs(ConfigBuilder, CS_Builder)

    def test_exceptions(self):
        from config_stash import ConfigLoadError as CL
        from config_stash import ConfigStashError as CS
        from config_stash import ConfigValidationError as CV
        from cs import ConfigLoadError, ConfigStashError, ConfigValidationError

        self.assertIs(ConfigStashError, CS)
        self.assertIs(ConfigLoadError, CL)
        self.assertIs(ConfigValidationError, CV)

    def test_loaders(self):
        from config_stash.loaders import EnvFileLoader as EFL
        from config_stash.loaders import EnvironmentLoader as EL
        from config_stash.loaders import IniLoader as IL
        from config_stash.loaders import JsonLoader as JL
        from config_stash.loaders import TomlLoader as TL
        from config_stash.loaders import YamlLoader as YL
        from cs.loaders import (
            EnvFileLoader,
            EnvironmentLoader,
            IniLoader,
            JsonLoader,
            TomlLoader,
            YamlLoader,
        )

        self.assertIs(YamlLoader, YL)
        self.assertIs(JsonLoader, JL)
        self.assertIs(TomlLoader, TL)
        self.assertIs(IniLoader, IL)
        self.assertIs(EnvFileLoader, EFL)
        self.assertIs(EnvironmentLoader, EL)

    def test_secret_stores(self):
        from config_stash.secret_stores import DictSecretStore as DS
        from config_stash.secret_stores import SecretResolver as SR
        from config_stash.secret_stores import SecretStore as SS
        from cs.secret_stores import DictSecretStore, SecretResolver, SecretStore

        self.assertIs(SecretStore, SS)
        self.assertIs(SecretResolver, SR)
        self.assertIs(DictSecretStore, DS)

    def test_merge_strategies(self):
        from config_stash.merge_strategies import AdvancedConfigMerger as AM
        from config_stash.merge_strategies import MergeStrategy as MS
        from cs.merge_strategies import AdvancedConfigMerger, MergeStrategy

        self.assertIs(MergeStrategy, MS)
        self.assertIs(AdvancedConfigMerger, AM)

    def test_config_diff(self):
        from config_stash.config_diff import ConfigDiff as CD
        from config_stash.config_diff import ConfigDiffer as CDr
        from cs.config_diff import ConfigDiff, ConfigDiffer

        self.assertIs(ConfigDiff, CD)
        self.assertIs(ConfigDiffer, CDr)

    def test_version(self):
        import config_stash
        import cs

        self.assertEqual(cs.__version__, config_stash.__version__)

    def test_real_usage(self):
        """End-to-end: use cs alias to create a real config."""
        import os
        import tempfile

        import yaml

        from cs import Config
        from cs.loaders import YamlLoader

        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        yaml.dump({"default": {"host": "localhost", "port": 5432}}, tmp)
        tmp.close()

        try:
            config = Config(
                env="default",
                loaders=[YamlLoader(tmp.name)],
                dynamic_reloading=False,
            )
            self.assertEqual(config.host, "localhost")
            self.assertEqual(config.port, 5432)
        finally:
            os.unlink(tmp.name)


if __name__ == "__main__":
    unittest.main()
