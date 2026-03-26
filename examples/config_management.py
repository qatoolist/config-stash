#!/usr/bin/env python3
"""Config Management — reload, freeze, versioning, diff, drift detection, callbacks."""

import json
import os
import shutil
import tempfile

from config_stash import Config
from config_stash.loaders import EnvironmentLoader, JsonLoader, YamlLoader
from config_stash.merge_strategies import MergeStrategy

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _header(title: str) -> None:
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def _write_yaml(path: str, content: str) -> None:
    with open(path, "w") as f:
        f.write(content)


def _write_json(path: str, data: dict) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------------------------
# 1. Manual reload
# ---------------------------------------------------------------------------


def manual_reload() -> None:
    """Create config, modify file on disk, call config.reload(), show new values."""
    _header("1. Manual Reload")

    tmpdir = tempfile.mkdtemp()
    cfg_path = os.path.join(tmpdir, "app.yaml")

    _write_yaml(cfg_path, "server:\n  host: localhost\n  port: 8080\n")

    try:
        config = Config(
            loaders=[YamlLoader(cfg_path)],
        )
        print(f"Before reload  -> host={config.server.host}, port={config.server.port}")

        # Modify the file on disk
        _write_yaml(cfg_path, "server:\n  host: 0.0.0.0\n  port: 9090\n")

        config.reload(incremental=False)
        print(f"After  reload  -> host={config.server.host}, port={config.server.port}")
    finally:
        shutil.rmtree(tmpdir)


# ---------------------------------------------------------------------------
# 2. Incremental reload
# ---------------------------------------------------------------------------


def incremental_reload() -> None:
    """Show config.reload(incremental=True) vs incremental=False."""
    _header("2. Incremental vs Full Reload")

    tmpdir = tempfile.mkdtemp()
    base_path = os.path.join(tmpdir, "base.yaml")
    extra_path = os.path.join(tmpdir, "extra.json")

    _write_yaml(base_path, "app:\n  name: demo\n  version: 1\n")
    _write_json(extra_path, {"logging": {"level": "INFO"}})

    try:
        config = Config(
            loaders=[YamlLoader(base_path), JsonLoader(extra_path)],
        )
        print(
            f"Initial        -> app.version={config.app.version}, "
            f"logging.level={config.logging.level}"
        )

        # Only modify base.yaml; extra.json stays the same
        _write_yaml(base_path, "app:\n  name: demo\n  version: 2\n")

        # Incremental reload — only changed files are re-read
        config.reload(incremental=True)
        print(
            f"Incremental    -> app.version={config.app.version}, "
            f"logging.level={config.logging.level}"
        )

        # Full reload — all files are re-read from scratch
        _write_yaml(base_path, "app:\n  name: demo\n  version: 3\n")
        config.reload(incremental=False)
        print(
            f"Full reload    -> app.version={config.app.version}, "
            f"logging.level={config.logging.level}"
        )
    finally:
        shutil.rmtree(tmpdir)


# ---------------------------------------------------------------------------
# 3. Dry-run reload
# ---------------------------------------------------------------------------


def dry_run_reload() -> None:
    """Modify file, call config.reload(dry_run=True), show values did not change."""
    _header("3. Dry-Run Reload")

    tmpdir = tempfile.mkdtemp()
    cfg_path = os.path.join(tmpdir, "app.yaml")

    _write_yaml(cfg_path, "feature:\n  enabled: false\n  max_retries: 3\n")

    try:
        config = Config(
            loaders=[YamlLoader(cfg_path)],
        )
        print(
            f"Before         -> enabled={config.feature.enabled}, "
            f"max_retries={config.feature.max_retries}"
        )

        # Change file on disk
        _write_yaml(cfg_path, "feature:\n  enabled: true\n  max_retries: 10\n")

        # Dry-run: Config-Stash loads the new values but does NOT apply them
        config.reload(dry_run=True, incremental=False)
        print(
            f"After dry-run  -> enabled={config.feature.enabled}, "
            f"max_retries={config.feature.max_retries}"
        )
        print("  (values unchanged — dry run discards new data)")
    finally:
        shutil.rmtree(tmpdir)


# ---------------------------------------------------------------------------
# 4. on_change callbacks
# ---------------------------------------------------------------------------


def on_change_callbacks() -> None:
    """Register @config.on_change callback, reload, show callback fired."""
    _header("4. on_change Callbacks")

    tmpdir = tempfile.mkdtemp()
    cfg_path = os.path.join(tmpdir, "app.yaml")

    _write_yaml(cfg_path, "database:\n  host: localhost\n  pool_size: 5\n")

    try:
        config = Config(
            loaders=[YamlLoader(cfg_path)],
        )

        changes: list = []

        @config.on_change
        def _on_config_change(key: str, old_value, new_value):  # type: ignore[no-untyped-def]
            changes.append((key, old_value, new_value))

        # Modify and reload so the callback fires
        _write_yaml(cfg_path, "database:\n  host: prod-db.internal\n  pool_size: 20\n")
        config.reload(incremental=False)

        print("Callback received the following changes:")
        for key, old_val, new_val in changes:
            print(f"  key={key!r:20s}  old={old_val!r:30s}  new={new_val!r}")
    finally:
        shutil.rmtree(tmpdir)


# ---------------------------------------------------------------------------
# 5. freeze()
# ---------------------------------------------------------------------------


def freeze_config() -> None:
    """Load config, freeze it, show that set() raises RuntimeError."""
    _header("5. freeze()")

    tmpdir = tempfile.mkdtemp()
    cfg_path = os.path.join(tmpdir, "app.yaml")

    _write_yaml(cfg_path, "api:\n  url: https://api.example.com\n  timeout: 30\n")

    try:
        config = Config(
            loaders=[YamlLoader(cfg_path)],
        )

        # Reads work before freeze
        print(f"Before freeze  -> api.url={config.api.url}")

        config.freeze()
        print(f"is_frozen      -> {config.is_frozen}")

        # Reads still work after freeze
        print(f"After freeze   -> api.timeout={config.api.timeout}")

        # Writes raise RuntimeError
        try:
            config.set("api.timeout", 60)
        except RuntimeError as exc:
            print(f"set() raised   -> {exc}")

        # reload() also raises RuntimeError
        try:
            config.reload()
        except RuntimeError as exc:
            print(f"reload() raised -> {exc}")
    finally:
        shutil.rmtree(tmpdir)


# ---------------------------------------------------------------------------
# 6. env_prefix
# ---------------------------------------------------------------------------


def env_prefix_loading() -> None:
    """Show Config(env_prefix='MYAPP') auto-loading from MYAPP_* env vars."""
    _header("6. env_prefix")

    tmpdir = tempfile.mkdtemp()
    cfg_path = os.path.join(tmpdir, "base.yaml")

    _write_yaml(cfg_path, "database:\n  host: localhost\n  port: 5432\n")

    # Set environment variables that the EnvironmentLoader will pick up.
    # The default separator is "__" (double underscore) for nested keys.
    # MYAPP_CACHE__TTL  ->  {"cache": {"ttl": "300"}}
    os.environ["MYAPP_CACHE__TTL"] = "300"
    os.environ["MYAPP_CACHE__BACKEND"] = "redis"

    try:
        config = Config(
            loaders=[YamlLoader(cfg_path)],
            env_prefix="MYAPP",
        )

        print(f"From YAML      -> database.host={config.database.host}")
        print(f"From YAML      -> database.port={config.database.port}")
        print(f"From env var   -> cache.ttl={config.cache.ttl}")
        print(f"From env var   -> cache.backend={config.cache.backend}")
    finally:
        os.environ.pop("MYAPP_CACHE__TTL", None)
        os.environ.pop("MYAPP_CACHE__BACKEND", None)
        shutil.rmtree(tmpdir)


# ---------------------------------------------------------------------------
# 7. merge_strategy
# ---------------------------------------------------------------------------


def merge_strategy_demo() -> None:
    """Show Config(merge_strategy=..., merge_strategy_map={...})."""
    _header("7. merge_strategy")

    tmpdir = tempfile.mkdtemp()
    base_path = os.path.join(tmpdir, "base.yaml")
    override_path = os.path.join(tmpdir, "override.json")

    _write_yaml(
        base_path,
        "database:\n  host: localhost\n  port: 5432\n  options:\n    timeout: 30\n"
        "logging:\n  level: INFO\n  handlers:\n    - console\n",
    )
    _write_json(
        override_path,
        {
            "database": {"port": 3306, "ssl": True},
            "logging": {"level": "DEBUG", "handlers": ["file"]},
        },
    )

    try:
        # Default strategy is MERGE (deep-merge dicts), but "database" is
        # set to REPLACE — the entire database block is replaced wholesale.
        config = Config(
            loaders=[YamlLoader(base_path), JsonLoader(override_path)],
            merge_strategy=MergeStrategy.MERGE,
            merge_strategy_map={"database": MergeStrategy.REPLACE},
        )

        print("database block (REPLACE — base values like 'host' are gone):")
        print(f"  database = {json.dumps(config.get('database'), indent=4)}")

        print("\nlogging block (MERGE — keys from both sources are combined):")
        print(f"  logging  = {json.dumps(config.get('logging'), indent=4)}")
    finally:
        shutil.rmtree(tmpdir)


# ---------------------------------------------------------------------------
# 8. Versioning
# ---------------------------------------------------------------------------


def versioning_demo() -> None:
    """Enable versioning, save snapshots, modify, rollback."""
    _header("8. Versioning")

    tmpdir = tempfile.mkdtemp()
    cfg_path = os.path.join(tmpdir, "app.yaml")
    versions_dir = os.path.join(tmpdir, "versions")

    _write_yaml(cfg_path, "app:\n  name: my-service\n  version: 1.0.0\n")

    try:
        config = Config(
            loaders=[YamlLoader(cfg_path)],
        )

        config.enable_versioning(storage_path=versions_dir)

        # Save first version
        v1 = config.save_version(
            metadata={"author": "alice", "message": "initial release"}
        )
        print(f"v1 saved       -> id={v1.version_id}, app.version={config.app.version}")

        # Modify config and save second version
        _write_yaml(cfg_path, "app:\n  name: my-service\n  version: 2.0.0\n")
        config.reload(incremental=False)

        v2 = config.save_version(metadata={"author": "bob", "message": "major upgrade"})
        print(f"v2 saved       -> id={v2.version_id}, app.version={config.app.version}")

        # Rollback to v1
        config.rollback_to_version(v1.version_id)
        print(f"After rollback -> app.version={config.app.version}  (restored v1)")
    finally:
        shutil.rmtree(tmpdir)


# ---------------------------------------------------------------------------
# 9. Config diff
# ---------------------------------------------------------------------------


def config_diff_demo() -> None:
    """Create two configs, call config1.diff(config2), print diffs."""
    _header("9. Config Diff")

    tmpdir = tempfile.mkdtemp()
    path_a = os.path.join(tmpdir, "a.yaml")
    path_b = os.path.join(tmpdir, "b.yaml")

    _write_yaml(
        path_a,
        "database:\n  host: localhost\n  port: 5432\ncache:\n  ttl: 60\n",
    )
    _write_yaml(
        path_b,
        "database:\n  host: prod-db\n  port: 5432\n  ssl: true\nredis:\n  url: redis://r1\n",
    )

    try:
        config_a = Config(loaders=[YamlLoader(path_a)])
        config_b = Config(loaders=[YamlLoader(path_b)])

        diffs = config_a.diff(config_b)

        print(f"Found {len(diffs)} top-level difference(s):\n")
        for d in diffs:
            info = d.to_dict()
            print(f"  [{info['type']:8s}]  path={info['path']!r}", end="")
            if "old_value" in info:
                print(f"  old={info['old_value']!r}", end="")
            if "new_value" in info:
                print(f"  new={info['new_value']!r}", end="")
            print()
            # Print nested diffs (e.g. inside 'database')
            for nd in d.nested_diffs:
                ni = nd.to_dict()
                print(f"    [{ni['type']:8s}]  path={ni['path']!r}", end="")
                if "old_value" in ni:
                    print(f"  old={ni['old_value']!r}", end="")
                if "new_value" in ni:
                    print(f"  new={ni['new_value']!r}", end="")
                print()
    finally:
        shutil.rmtree(tmpdir)


# ---------------------------------------------------------------------------
# 10. Drift detection
# ---------------------------------------------------------------------------


def drift_detection_demo() -> None:
    """actual.detect_drift(intended), show drift entries."""
    _header("10. Drift Detection")

    tmpdir = tempfile.mkdtemp()
    intended_path = os.path.join(tmpdir, "intended.yaml")
    actual_path = os.path.join(tmpdir, "actual.yaml")

    _write_yaml(
        intended_path,
        "database:\n  host: prod-db.internal\n  port: 5432\n  ssl: true\n"
        "logging:\n  level: WARNING\n",
    )
    _write_yaml(
        actual_path,
        "database:\n  host: dev-db.local\n  port: 5432\n  ssl: false\n"
        "logging:\n  level: DEBUG\n",
    )

    try:
        intended = Config(loaders=[YamlLoader(intended_path)])
        actual = Config(loaders=[YamlLoader(actual_path)])

        drift = actual.detect_drift(intended)

        if drift:
            print(f"Drift detected — {len(drift)} top-level difference(s):\n")
            for d in drift:
                info = d.to_dict()
                print(f"  [{info['type']:8s}]  path={info['path']!r}", end="")
                if "old_value" in info:
                    print(f"  intended={info['old_value']!r}", end="")
                if "new_value" in info:
                    print(f"  actual={info['new_value']!r}", end="")
                print()
                for nd in d.nested_diffs:
                    ni = nd.to_dict()
                    print(f"    [{ni['type']:8s}]  path={ni['path']!r}", end="")
                    if "old_value" in ni:
                        print(f"  intended={ni['old_value']!r}", end="")
                    if "new_value" in ni:
                        print(f"  actual={ni['new_value']!r}", end="")
                    print()
        else:
            print("No drift detected.")
    finally:
        shutil.rmtree(tmpdir)


# ---------------------------------------------------------------------------
# 11. config.layers
# ---------------------------------------------------------------------------


def layers_demo() -> None:
    """Load from 2 sources, print config.layers showing precedence."""
    _header("11. config.layers (source precedence)")

    tmpdir = tempfile.mkdtemp()
    base_path = os.path.join(tmpdir, "defaults.yaml")
    override_path = os.path.join(tmpdir, "overrides.json")

    _write_yaml(
        base_path,
        "app:\n  name: my-service\n  debug: false\ndatabase:\n  host: localhost\n",
    )
    _write_json(
        override_path,
        {"app": {"debug": True}, "feature_flags": {"new_ui": True}},
    )

    try:
        config = Config(
            loaders=[YamlLoader(base_path), JsonLoader(override_path)],
        )

        print("Layers (lowest priority first):\n")
        for idx, layer in enumerate(config.layers):
            print(f"  Layer {idx}:")
            print(f"    source      = {layer['source']}")
            print(f"    loader_type = {layer['loader_type']}")
            print(f"    key_count   = {layer['key_count']}")
            print(f"    keys        = {layer['keys']}")
            print()

        print(
            f"Resolved app.debug = {config.app.debug}  " "(override wins over default)"
        )
    finally:
        shutil.rmtree(tmpdir)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Run every example in sequence."""
    print("=" * 70)
    print("  Config-Stash — Config Management Examples")
    print("=" * 70)

    manual_reload()
    incremental_reload()
    dry_run_reload()
    on_change_callbacks()
    freeze_config()
    env_prefix_loading()
    merge_strategy_demo()
    versioning_demo()
    config_diff_demo()
    drift_detection_demo()
    layers_demo()

    print("\n" + "=" * 70)
    print("  All config management examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
