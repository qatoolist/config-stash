"""Tests for the `cs` short alias package.

Verifies that `from cs import X` works identically to `from config_stash import X`.
"""

import unittest


class TestCsAlias(unittest.TestCase):
    """Verify cs.* imports resolve to the same objects as config_stash.*"""

    def test_top_level_imports(self):
        from cs import Config, ConfigBuilder

        from config_stash import Config as CS_Config
        from config_stash import ConfigBuilder as CS_Builder

        self.assertIs(Config, CS_Config)
        self.assertIs(ConfigBuilder, CS_Builder)

    def test_exceptions(self):
        from cs import (
            ConfigLoadError,
            ConfigStashError,
            ConfigValidationError,
        )

        from config_stash import (
            ConfigLoadError as CL,
            ConfigStashError as CS,
            ConfigValidationError as CV,
        )

        self.assertIs(ConfigStashError, CS)
        self.assertIs(ConfigLoadError, CL)
        self.assertIs(ConfigValidationError, CV)

    def test_loaders(self):
        from cs.loaders import (
            EnvFileLoader,
            EnvironmentLoader,
            IniLoader,
            JsonLoader,
            TomlLoader,
            YamlLoader,
        )

        from config_stash.loaders import (
            EnvFileLoader as EFL,
            EnvironmentLoader as EL,
            IniLoader as IL,
            JsonLoader as JL,
            TomlLoader as TL,
            YamlLoader as YL,
        )

        self.assertIs(YamlLoader, YL)
        self.assertIs(JsonLoader, JL)
        self.assertIs(TomlLoader, TL)
        self.assertIs(IniLoader, IL)
        self.assertIs(EnvFileLoader, EFL)
        self.assertIs(EnvironmentLoader, EL)

    def test_secret_stores(self):
        from cs.secret_stores import DictSecretStore, SecretResolver, SecretStore

        from config_stash.secret_stores import (
            DictSecretStore as DS,
            SecretResolver as SR,
            SecretStore as SS,
        )

        self.assertIs(SecretStore, SS)
        self.assertIs(SecretResolver, SR)
        self.assertIs(DictSecretStore, DS)

    def test_merge_strategies(self):
        from cs.merge_strategies import AdvancedConfigMerger, MergeStrategy

        from config_stash.merge_strategies import (
            AdvancedConfigMerger as AM,
            MergeStrategy as MS,
        )

        self.assertIs(MergeStrategy, MS)
        self.assertIs(AdvancedConfigMerger, AM)

    def test_config_diff(self):
        from cs.config_diff import ConfigDiff, ConfigDiffer

        from config_stash.config_diff import (
            ConfigDiff as CD,
            ConfigDiffer as CDr,
        )

        self.assertIs(ConfigDiff, CD)
        self.assertIs(ConfigDiffer, CDr)

    def test_version(self):
        import cs
        import config_stash

        self.assertEqual(cs.__version__, config_stash.__version__)

    def test_real_usage(self):
        """End-to-end: use cs alias to create a real config."""
        import os
        import tempfile

        import yaml

        from cs import Config
        from cs.loaders import YamlLoader

        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        )
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
