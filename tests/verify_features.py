#!/usr/bin/env python3
"""
End-to-end feature verification for config-stash.
Runs REAL code with REAL files -- no mocks.
Each test prints PASS/FAIL with feature name.
"""

import json
import os
import shutil
import sys
import tempfile
import traceback

# Ensure the source tree is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

results = []


def run_test(name, fn):
    """Run a single test, capture PASS/FAIL."""
    try:
        fn()
        print(f"PASS: {name}")
        results.append((name, True, None))
    except Exception as e:
        tb = traceback.format_exc()
        print(f"FAIL: {name}\n      Error: {e}\n{tb}")
        results.append((name, False, str(e)))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_tmp():
    """Return a fresh temp directory that the caller must clean up."""
    return tempfile.mkdtemp(prefix="cfgstash_verify_")


# ===========================================================================
# 1. YAML loading
# ===========================================================================
def test_yaml_loading():
    tmp = make_tmp()
    try:
        path = os.path.join(tmp, "cfg.yaml")
        with open(path, "w") as f:
            f.write("database:\n  host: myhost\n  port: 5432\n")

        from config_stash import Config
        from config_stash.loaders import YamlLoader

        cfg = Config(loaders=[YamlLoader(path)], enable_ide_support=False)
        d = cfg.to_dict()
        assert (
            d["database"]["host"] == "myhost"
        ), f"Expected 'myhost', got {d['database']['host']}"
        assert (
            d["database"]["port"] == 5432
        ), f"Expected 5432, got {d['database']['port']}"
    finally:
        shutil.rmtree(tmp)


# ===========================================================================
# 2. JSON loading
# ===========================================================================
def test_json_loading():
    tmp = make_tmp()
    try:
        path = os.path.join(tmp, "cfg.json")
        with open(path, "w") as f:
            json.dump({"app": {"name": "TestApp", "debug": True}}, f)

        from config_stash import Config
        from config_stash.loaders import JsonLoader

        cfg = Config(loaders=[JsonLoader(path)], enable_ide_support=False)
        d = cfg.to_dict()
        assert d["app"]["name"] == "TestApp"
        assert d["app"]["debug"] is True
    finally:
        shutil.rmtree(tmp)


# ===========================================================================
# 3. TOML loading
# ===========================================================================
def test_toml_loading():
    tmp = make_tmp()
    try:
        path = os.path.join(tmp, "cfg.toml")
        with open(path, "w") as f:
            f.write('[server]\nhost = "0.0.0.0"\nport = 8080\n')

        from config_stash import Config
        from config_stash.loaders import TomlLoader

        cfg = Config(loaders=[TomlLoader(path)], enable_ide_support=False)
        d = cfg.to_dict()
        assert d["server"]["host"] == "0.0.0.0"
        assert d["server"]["port"] == 8080
    finally:
        shutil.rmtree(tmp)


# ===========================================================================
# 4. INI loading
# ===========================================================================
def test_ini_loading():
    tmp = make_tmp()
    try:
        path = os.path.join(tmp, "cfg.ini")
        with open(path, "w") as f:
            f.write("[section1]\nkey1 = hello\nkey2 = 42\n")

        from config_stash import Config
        from config_stash.loaders import IniLoader

        cfg = Config(loaders=[IniLoader(path)], enable_ide_support=False)
        d = cfg.to_dict()
        assert d["section1"]["key1"] == "hello", f"Got {d['section1']['key1']}"
        assert d["section1"]["key2"] == 42, f"Got {d['section1']['key2']}"
    finally:
        shutil.rmtree(tmp)


# ===========================================================================
# 5. .env loading
# ===========================================================================
def test_env_file_loading():
    tmp = make_tmp()
    try:
        path = os.path.join(tmp, ".env")
        with open(path, "w") as f:
            f.write("MY_KEY=myvalue\nMY_NUM=99\n")

        from config_stash import Config
        from config_stash.loaders import EnvFileLoader

        cfg = Config(loaders=[EnvFileLoader(path)], enable_ide_support=False)
        d = cfg.to_dict()
        assert d["MY_KEY"] == "myvalue", f"Got {d.get('MY_KEY')}"
        assert d["MY_NUM"] == 99, f"Got {d.get('MY_NUM')}"
    finally:
        shutil.rmtree(tmp)


# ===========================================================================
# 6. Environment variable loading
# ===========================================================================
def test_env_var_loading():
    prefix = "CFGSTASHTEST"
    # Double underscore (__) is the nesting separator
    os.environ[f"{prefix}_DB__HOST"] = "envhost"
    os.environ[f"{prefix}_DB__PORT"] = "3306"
    try:
        from config_stash import Config
        from config_stash.loaders import EnvironmentLoader

        cfg = Config(loaders=[EnvironmentLoader(prefix)], enable_ide_support=False)
        d = cfg.to_dict()
        assert d["db"]["host"] == "envhost", f"Got {d}"
        assert str(d["db"]["port"]) == "3306", f"Got {d['db']['port']}"
    finally:
        del os.environ[f"{prefix}_DB__HOST"]
        del os.environ[f"{prefix}_DB__PORT"]


# ===========================================================================
# 7. Multi-source merge
# ===========================================================================
def test_multi_source_merge():
    tmp = make_tmp()
    try:
        yaml_path = os.path.join(tmp, "base.yaml")
        json_path = os.path.join(tmp, "override.json")

        with open(yaml_path, "w") as f:
            f.write("app:\n  name: BaseApp\n  version: '1.0'\n")
        with open(json_path, "w") as f:
            json.dump({"app": {"name": "OverrideApp"}}, f)

        from config_stash import Config
        from config_stash.loaders import JsonLoader, YamlLoader

        cfg = Config(
            loaders=[YamlLoader(yaml_path), JsonLoader(json_path)],
            enable_ide_support=False,
        )
        d = cfg.to_dict()
        # JSON loaded second should override YAML
        assert d["app"]["name"] == "OverrideApp", f"Got {d['app']['name']}"
        # YAML-only key should still be present
        assert d["app"]["version"] == "1.0", f"Got {d['app'].get('version')}"
    finally:
        shutil.rmtree(tmp)


# ===========================================================================
# 8. Deep merge
# ===========================================================================
def test_deep_merge():
    tmp = make_tmp()
    try:
        y1 = os.path.join(tmp, "a.yaml")
        y2 = os.path.join(tmp, "b.yaml")
        with open(y1, "w") as f:
            f.write("database:\n  host: localhost\n  port: 5432\n")
        with open(y2, "w") as f:
            f.write("database:\n  port: 3306\n  name: mydb\n")

        from config_stash import Config
        from config_stash.loaders import YamlLoader

        cfg = Config(
            loaders=[YamlLoader(y1), YamlLoader(y2)],
            deep_merge=True,
            enable_ide_support=False,
        )
        d = cfg.to_dict()
        assert d["database"]["host"] == "localhost", "host should survive deep merge"
        assert d["database"]["port"] == 3306, "port should be overridden"
        assert d["database"]["name"] == "mydb", "name should be added"
    finally:
        shutil.rmtree(tmp)


# ===========================================================================
# 9. Environment resolution (default + production sections)
# ===========================================================================
def test_environment_resolution():
    tmp = make_tmp()
    try:
        path = os.path.join(tmp, "env.yaml")
        with open(path, "w") as f:
            f.write(
                "default:\n  db_host: localhost\n  db_port: 5432\n"
                "production:\n  db_host: prod-db.example.com\n"
            )

        from config_stash import Config
        from config_stash.loaders import YamlLoader

        cfg = Config(
            env="production",
            loaders=[YamlLoader(path)],
            enable_ide_support=False,
        )
        d = cfg.to_dict()
        assert d["db_host"] == "prod-db.example.com", f"Got {d.get('db_host')}"
        # default port should carry over
        assert d["db_port"] == 5432, f"Got {d.get('db_port')}"
    finally:
        shutil.rmtree(tmp)


# ===========================================================================
# 10. Attribute access
# ===========================================================================
def test_attribute_access():
    tmp = make_tmp()
    try:
        path = os.path.join(tmp, "attr.yaml")
        with open(path, "w") as f:
            f.write("database:\n  host: attrhost\n  port: 9999\n")

        from config_stash import Config
        from config_stash.loaders import YamlLoader

        cfg = Config(loaders=[YamlLoader(path)], enable_ide_support=False)
        host = cfg.database.host
        port = cfg.database.port
        assert host == "attrhost", f"Got {host}"
        assert port == 9999, f"Got {port}"
    finally:
        shutil.rmtree(tmp)


# ===========================================================================
# 11. Hook processing
# ===========================================================================
def test_hook_processing():
    tmp = make_tmp()
    try:
        path = os.path.join(tmp, "hook.yaml")
        with open(path, "w") as f:
            f.write("greeting: hello\n")

        from config_stash import Config
        from config_stash.loaders import YamlLoader

        cfg = Config(
            loaders=[YamlLoader(path)],
            use_env_expander=False,
            use_type_casting=False,
            enable_ide_support=False,
        )
        cfg.register_key_hook("greeting", lambda v: v.upper())
        val = cfg.get("greeting")
        assert val == "HELLO", f"Got {val}"
    finally:
        shutil.rmtree(tmp)


# ===========================================================================
# 12. Config reload
# ===========================================================================
def test_config_reload():
    tmp = make_tmp()
    try:
        path = os.path.join(tmp, "reload.yaml")
        with open(path, "w") as f:
            f.write("value: original\n")

        from config_stash import Config
        from config_stash.loaders import YamlLoader

        cfg = Config(loaders=[YamlLoader(path)], enable_ide_support=False)
        assert cfg.to_dict()["value"] == "original"

        # Modify file
        with open(path, "w") as f:
            f.write("value: updated\n")

        cfg.reload(incremental=False)
        assert cfg.to_dict()["value"] == "updated", f"Got {cfg.to_dict()['value']}"
    finally:
        shutil.rmtree(tmp)


# ===========================================================================
# 13. Config set()
# ===========================================================================
def test_config_set():
    tmp = make_tmp()
    try:
        path = os.path.join(tmp, "settest.yaml")
        with open(path, "w") as f:
            f.write("app:\n  name: before\n")

        from config_stash import Config
        from config_stash.loaders import YamlLoader

        cfg = Config(loaders=[YamlLoader(path)], enable_ide_support=False)
        cfg.set("app.name", "after")
        assert cfg.get("app.name") == "after", f"Got {cfg.get('app.name')}"

        # Set a brand-new nested key
        cfg.set("app.new_key", "new_val")
        assert cfg.get("app.new_key") == "new_val"
    finally:
        shutil.rmtree(tmp)


# ===========================================================================
# 14. Config versioning
# ===========================================================================
def test_config_versioning():
    tmp = make_tmp()
    try:
        path = os.path.join(tmp, "ver.yaml")
        with open(path, "w") as f:
            f.write("val: v1\n")

        ver_dir = os.path.join(tmp, "versions")

        from config_stash import Config
        from config_stash.loaders import YamlLoader

        cfg = Config(loaders=[YamlLoader(path)], enable_ide_support=False)
        mgr = cfg.enable_versioning(storage_path=ver_dir)

        v1 = cfg.save_version(metadata={"msg": "initial"})
        assert v1 is not None
        v1_id = v1.version_id

        # Mutate config and save another version
        cfg.set("val", "v2")
        v2 = cfg.save_version(metadata={"msg": "second"})
        assert v2 is not None
        assert cfg.get("val") == "v2"

        # Rollback to v1
        cfg.rollback_to_version(v1_id)
        assert cfg.get("val") == "v1", f"Got {cfg.get('val')}"
    finally:
        shutil.rmtree(tmp)


# ===========================================================================
# 15. Config diff
# ===========================================================================
def test_config_diff():
    from config_stash.config_diff import ConfigDiffer, DiffType

    c1 = {"a": 1, "b": 2, "c": {"x": 10}}
    c2 = {"a": 1, "b": 99, "c": {"x": 10, "y": 20}, "d": "new"}
    diffs = ConfigDiffer.diff(c1, c2)
    types = {d.key: d.diff_type for d in diffs}
    assert types["b"] == DiffType.MODIFIED
    assert types["d"] == DiffType.ADDED
    # "c" should show as modified because of nested addition
    assert types["c"] == DiffType.MODIFIED

    summary = ConfigDiffer.diff_summary(diffs)
    assert summary["total"] > 0


# ===========================================================================
# 16. Config export
# ===========================================================================
def test_config_export():
    tmp = make_tmp()
    try:
        path = os.path.join(tmp, "exp.yaml")
        with open(path, "w") as f:
            f.write("export_key: export_val\n")

        from config_stash import Config
        from config_stash.loaders import YamlLoader

        cfg = Config(loaders=[YamlLoader(path)], enable_ide_support=False)

        json_str = cfg.export(format="json")
        parsed = json.loads(json_str)
        assert parsed["export_key"] == "export_val"

        yaml_str = cfg.export(format="yaml")
        assert "export_key" in yaml_str
    finally:
        shutil.rmtree(tmp)


# ===========================================================================
# 17. Composition (_include)
# ===========================================================================
def test_composition_include():
    tmp = make_tmp()
    try:
        base_path = os.path.join(tmp, "base.yaml")
        main_path = os.path.join(tmp, "main.yaml")

        with open(base_path, "w") as f:
            f.write("shared:\n  color: blue\n")
        with open(main_path, "w") as f:
            f.write(f"_include:\n  - {base_path}\napp:\n  name: MainApp\n")

        from config_stash import Config
        from config_stash.loaders import YamlLoader

        cfg = Config(loaders=[YamlLoader(main_path)], enable_ide_support=False)
        d = cfg.to_dict()
        assert d["app"]["name"] == "MainApp"
        assert d["shared"]["color"] == "blue", f"Got {d.get('shared')}"
    finally:
        shutil.rmtree(tmp)


# ===========================================================================
# 18. Secret resolution (DictSecretStore)
# ===========================================================================
def test_secret_resolution():
    tmp = make_tmp()
    try:
        path = os.path.join(tmp, "sec.yaml")
        with open(path, "w") as f:
            f.write('db_password: "${secret:db/pass}"\napi_key: "${secret:api/key}"\n')

        from config_stash import Config
        from config_stash.loaders import YamlLoader
        from config_stash.secret_stores.providers.dict_secret_store import (
            DictSecretStore,
        )
        from config_stash.secret_stores.resolver import SecretResolver

        store = DictSecretStore({"db/pass": "s3cret", "api/key": "APIKEY123"})
        resolver = SecretResolver(store)

        cfg = Config(
            loaders=[YamlLoader(path)],
            secret_resolver=resolver,
            enable_ide_support=False,
        )
        assert cfg.get("db_password") == "s3cret", f"Got {cfg.get('db_password')}"
        assert cfg.get("api_key") == "APIKEY123", f"Got {cfg.get('api_key')}"
    finally:
        shutil.rmtree(tmp)


# ===========================================================================
# 19. Config keys / has / get methods
# ===========================================================================
def test_keys_has_get():
    tmp = make_tmp()
    try:
        path = os.path.join(tmp, "khg.yaml")
        with open(path, "w") as f:
            f.write("level1:\n  level2:\n    val: deep\ntop: hi\n")

        from config_stash import Config
        from config_stash.loaders import YamlLoader

        cfg = Config(loaders=[YamlLoader(path)], enable_ide_support=False)

        all_keys = cfg.keys()
        assert "top" in all_keys, f"Keys: {all_keys}"
        assert "level1" in all_keys

        assert cfg.has("top") is True
        assert cfg.has("level1.level2.val") is True
        assert cfg.has("nonexistent") is False

        assert cfg.get("top") == "hi"
        assert cfg.get("level1.level2.val") == "deep"
        assert cfg.get("missing", "default_val") == "default_val"
    finally:
        shutil.rmtree(tmp)


# ===========================================================================
# 20. on_change callback
# ===========================================================================
def test_on_change_callback():
    tmp = make_tmp()
    try:
        path = os.path.join(tmp, "chg.yaml")
        with open(path, "w") as f:
            f.write("color: red\n")

        from config_stash import Config
        from config_stash.loaders import YamlLoader

        cfg = Config(loaders=[YamlLoader(path)], enable_ide_support=False)

        changes = []

        @cfg.on_change
        def handler(key, old_val, new_val):
            changes.append((key, old_val, new_val))

        # Modify and reload
        with open(path, "w") as f:
            f.write("color: green\n")

        cfg.reload(incremental=False)

        assert len(changes) > 0, "on_change callback was never fired"
        # Find the color change
        color_changes = [c for c in changes if c[0] == "color"]
        assert len(color_changes) == 1, f"Expected 1 color change, got {color_changes}"
        assert color_changes[0][1] == "red"
        assert color_changes[0][2] == "green"
    finally:
        shutil.rmtree(tmp)


# ===========================================================================
# 21. ConfigBuilder
# ===========================================================================
def test_config_builder():
    tmp = make_tmp()
    try:
        path = os.path.join(tmp, "bldr.yaml")
        with open(path, "w") as f:
            f.write("default:\n  mode: base\nproduction:\n  mode: prod\n")

        from config_stash import ConfigBuilder
        from config_stash.loaders import YamlLoader

        cfg = (
            ConfigBuilder()
            .with_env("production")
            .add_loader(YamlLoader(path))
            .disable_ide_support()
            .build()
        )
        assert cfg.get("mode") == "prod", f"Got {cfg.get('mode')}"
    finally:
        shutil.rmtree(tmp)


# ===========================================================================
# 22. Pydantic validation
# ===========================================================================
def test_pydantic_validation():
    try:
        from pydantic import BaseModel
    except ImportError:
        raise RuntimeError("pydantic not installed -- skipping")

    from config_stash.validators.pydantic_validator import PydanticValidator

    class MyModel(BaseModel):
        host: str
        port: int = 5432

    validator = PydanticValidator(MyModel)
    result = validator.validate({"host": "localhost", "port": 9999})
    assert result.host == "localhost"
    assert result.port == 9999

    # Verify default value
    result2 = validator.validate({"host": "abc"})
    assert result2.port == 5432

    # Verify validation failure
    try:
        validator.validate({"port": "not_a_number"})
        raise AssertionError("Should have raised ConfigValidationError")
    except Exception as e:
        assert "validation" in str(e).lower() or "Validation" in str(type(e).__name__)


# ===========================================================================
# 23. JSON Schema validation
# ===========================================================================
def test_json_schema_validation():
    try:
        import jsonschema  # noqa: F401
    except ImportError:
        raise RuntimeError("jsonschema not installed -- skipping")

    from config_stash.validators.schema_validator import SchemaValidator

    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "count": {"type": "integer"},
        },
        "required": ["name"],
    }

    validator = SchemaValidator(schema)
    assert validator.validate({"name": "test", "count": 5}) is True

    # Missing required field
    try:
        validator.validate({"count": 5})
        raise AssertionError("Should have raised ValidationError")
    except Exception as e:
        # jsonschema raises ValidationError
        assert "name" in str(e).lower() or "required" in str(e).lower()


# ===========================================================================
# Run all tests
# ===========================================================================
if __name__ == "__main__":
    # Change to a temp dir so that default pyproject.toml discovery doesn't interfere
    original_cwd = os.getcwd()

    tests = [
        ("1. YAML loading", test_yaml_loading),
        ("2. JSON loading", test_json_loading),
        ("3. TOML loading", test_toml_loading),
        ("4. INI loading", test_ini_loading),
        ("5. .env loading", test_env_file_loading),
        ("6. Environment variable loading", test_env_var_loading),
        ("7. Multi-source merge", test_multi_source_merge),
        ("8. Deep merge", test_deep_merge),
        ("9. Environment resolution", test_environment_resolution),
        ("10. Attribute access", test_attribute_access),
        ("11. Hook processing", test_hook_processing),
        ("12. Config reload", test_config_reload),
        ("13. Config set()", test_config_set),
        ("14. Config versioning", test_config_versioning),
        ("15. Config diff", test_config_diff),
        ("16. Config export", test_config_export),
        ("17. Composition (_include)", test_composition_include),
        ("18. Secret resolution", test_secret_resolution),
        ("19. Config keys/has/get", test_keys_has_get),
        ("20. on_change callback", test_on_change_callback),
        ("21. ConfigBuilder", test_config_builder),
        ("22. Pydantic validation", test_pydantic_validation),
        ("23. JSON Schema validation", test_json_schema_validation),
    ]

    print("=" * 60)
    print("config-stash END-TO-END Feature Verification")
    print("=" * 60)
    print()

    for name, fn in tests:
        run_test(name, fn)

    print()
    print("=" * 60)
    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    print(f"Results: {passed} passed, {failed} failed, {len(results)} total")
    if failed:
        print("\nFailed tests:")
        for name, ok, err in results:
            if not ok:
                print(f"  - {name}: {err}")
    print("=" * 60)

    sys.exit(1 if failed else 0)
