#!/usr/bin/env python3
"""Extensibility — custom hooks, custom loaders, observability, events, composition."""

import json
import os
import re
import tempfile
from typing import Any, Dict, Optional

from cs import Config
from cs.loaders import Loader, YamlLoader

# ---------------------------------------------------------------------------
# 1. Custom global hook — uppercase all string values
# ---------------------------------------------------------------------------


def example_global_hook():
    """Register a global hook that uppercases every string value."""
    print("\n" + "=" * 70)
    print("1. Custom Global Hook — Uppercase All Strings")
    print("=" * 70)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(
            "app:\n" "  name: my-application\n" "  region: us-east-1\n" "  version: 3\n"
        )
        config_file = f.name

    try:
        config = Config(
            loaders=[YamlLoader(config_file)],
            use_env_expander=False,
            use_type_casting=False,
        )

        def uppercase_strings(value: Any) -> Any:
            """Hook: uppercase every string value."""
            if isinstance(value, str):
                return value.upper()
            return value

        config.register_global_hook(uppercase_strings)

        print(f"  app.name   -> {config.get('app.name')}")
        print(f"  app.region -> {config.get('app.region')}")
        print(f"  app.version (int, unaffected) -> {config.get('app.version')}")
    finally:
        os.unlink(config_file)


# ---------------------------------------------------------------------------
# 2. Custom key hook — mask database.password
# ---------------------------------------------------------------------------


def example_key_hook():
    """Register a key hook that masks the database password."""
    print("\n" + "=" * 70)
    print("2. Custom Key Hook — Mask database.password")
    print("=" * 70)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(
            "database:\n" "  host: db.example.com\n" "  password: super-secret-123\n"
        )
        config_file = f.name

    try:
        config = Config(
            loaders=[YamlLoader(config_file)],
            use_env_expander=False,
            use_type_casting=False,
        )

        config.register_key_hook("database.password", lambda _v: "****")

        print(f"  database.host     -> {config.get('database.host')}")
        print(f"  database.password -> {config.get('database.password')}")
    finally:
        os.unlink(config_file)


# ---------------------------------------------------------------------------
# 3. Custom condition hook — expand ${VAR} placeholders manually
# ---------------------------------------------------------------------------


def example_condition_hook():
    """Register a condition hook that expands ${...} variable references."""
    print("\n" + "=" * 70)
    print("3. Custom Condition Hook — Expand ${...} Variables")
    print("=" * 70)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("greeting: Hello, ${USER_NAME}!\n" "static_value: no-variables-here\n")
        config_file = f.name

    os.environ["USER_NAME"] = "Alice"

    try:
        config = Config(
            loaders=[YamlLoader(config_file)],
            use_env_expander=False,
            use_type_casting=False,
        )

        def has_placeholder(_key: str, value: Any) -> bool:
            return isinstance(value, str) and "${" in value

        def expand_placeholders(value: Any) -> Any:
            """Replace ${VAR} with os.environ[VAR]."""

            def replacer(match: re.Match) -> str:
                var_name = match.group(1)
                return os.environ.get(var_name, match.group(0))

            return re.sub(r"\$\{(\w+)\}", replacer, value)

        config.register_condition_hook(has_placeholder, expand_placeholders)

        print(f"  greeting     -> {config.get('greeting')}")
        print(f"  static_value -> {config.get('static_value')}")
    finally:
        os.environ.pop("USER_NAME", None)
        os.unlink(config_file)


# ---------------------------------------------------------------------------
# 4. Custom loader — in-memory dict loader
# ---------------------------------------------------------------------------


class DictLoader(Loader):
    """A custom loader that serves configuration from a Python dict."""

    def __init__(self, data: Dict[str, Any], name: str = "dict") -> None:
        super().__init__(name)
        self._data = data

    def load(self) -> Optional[Dict[str, Any]]:
        return dict(self._data)


def example_custom_loader():
    """Create a custom loader that reads from a plain Python dict."""
    print("\n" + "=" * 70)
    print("4. Custom Loader — In-Memory DictLoader")
    print("=" * 70)

    data = {
        "feature_flags": {
            "dark_mode": True,
            "beta_api": False,
        },
        "limits": {
            "max_connections": 100,
        },
    }

    config = Config(
        loaders=[DictLoader(data, name="runtime-flags")],
    )

    print(f"  feature_flags.dark_mode      -> {config.feature_flags.dark_mode}")
    print(f"  feature_flags.beta_api       -> {config.feature_flags.beta_api}")
    print(f"  limits.max_connections       -> {config.limits.max_connections}")


# ---------------------------------------------------------------------------
# 5. Observability / metrics
# ---------------------------------------------------------------------------


def example_observability():
    """Enable observability, access keys, then inspect metrics."""
    print("\n" + "=" * 70)
    print("5. Observability / Metrics")
    print("=" * 70)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(
            "server:\n" "  host: 0.0.0.0\n" "  port: 8080\n" "cache:\n" "  ttl: 300\n"
        )
        config_file = f.name

    try:
        config = Config(
            loaders=[YamlLoader(config_file)],
        )

        config.enable_observability()

        # Access some keys to generate metrics
        _ = config.server.host
        _ = config.server.port
        _ = config.server.host  # second access
        _ = config.cache.ttl

        metrics = config.get_metrics()
        print(f"  Accessed keys : {metrics['accessed_keys']}")
        print(f"  Reload count  : {metrics['reload_count']}")
        print("  Top accessed  :")
        for entry in metrics.get("top_accessed_keys", []):
            print(f"    {entry['key']}: {entry['count']} accesses")
    finally:
        os.unlink(config_file)


# ---------------------------------------------------------------------------
# 6. Event emission — reload and change events
# ---------------------------------------------------------------------------


def example_event_emission():
    """Enable events, subscribe to reload and change, then trigger them."""
    print("\n" + "=" * 70)
    print("6. Event Emission — reload / change")
    print("=" * 70)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("service:\n" "  name: event-demo\n" "  version: 1\n")
        config_file = f.name

    try:
        config = Config(
            loaders=[YamlLoader(config_file)],
        )

        emitter = config.enable_events()

        events_log: list = []

        @emitter.on("reload")
        def on_reload(new_config: Any, duration: float) -> None:
            events_log.append(f"reload (took {duration:.4f}s)")

        @emitter.on("change")
        def on_change(old_config: Any, new_config: Any) -> None:
            events_log.append("change detected")

        # Trigger a reload (incremental=False forces full reload)
        config.reload(incremental=False)

        print("  Events fired:")
        for event in events_log:
            print(f"    - {event}")
        if not events_log:
            print("    (none)")
    finally:
        os.unlink(config_file)


# ---------------------------------------------------------------------------
# 7. Composition — _include directive
# ---------------------------------------------------------------------------


def example_composition_include():
    """Use _include to merge a base config into a main config."""
    print("\n" + "=" * 70)
    print("7. Composition — _include Directive")
    print("=" * 70)

    tmpdir = tempfile.mkdtemp()
    base_path = os.path.join(tmpdir, "base.yaml")
    main_path = os.path.join(tmpdir, "main.yaml")

    with open(base_path, "w") as f:
        f.write("defaults:\n" "  timeout: 30\n" "  retries: 3\n")

    with open(main_path, "w") as f:
        f.write("_include:\n" "  - base.yaml\n" "app:\n" "  name: composed-app\n")

    try:
        config = Config(
            loaders=[YamlLoader(main_path)],
        )

        print(f"  app.name         -> {config.app.name}")
        print(f"  defaults.timeout -> {config.defaults.timeout}")
        print(f"  defaults.retries -> {config.defaults.retries}")
    finally:
        os.unlink(base_path)
        os.unlink(main_path)
        os.rmdir(tmpdir)


# ---------------------------------------------------------------------------
# 8. Composition — _defaults directive
# ---------------------------------------------------------------------------


def example_composition_defaults():
    """Use _defaults to inject base key-value pairs into a config."""
    print("\n" + "=" * 70)
    print("8. Composition — _defaults Directive")
    print("=" * 70)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(
            "_defaults:\n"
            "  - log_level: info\n"
            "  - region: us-west-2\n"
            "app:\n"
            "  name: defaults-demo\n"
        )
        config_file = f.name

    try:
        config = Config(
            loaders=[YamlLoader(config_file)],
        )

        print(f"  app.name  -> {config.app.name}")
        print(f"  log_level -> {config.get('log_level')}")
        print(f"  region    -> {config.get('region')}")
    finally:
        os.unlink(config_file)


# ---------------------------------------------------------------------------
# 9. config.export() — JSON, YAML, TOML
# ---------------------------------------------------------------------------


def example_export():
    """Export configuration to JSON, YAML, and TOML strings."""
    print("\n" + "=" * 70)
    print("9. config.export() — JSON, YAML, TOML")
    print("=" * 70)

    data = {
        "server": {"host": "0.0.0.0", "port": 9090},
        "logging": {"level": "debug"},
    }

    config = Config(
        loaders=[DictLoader(data)],
    )

    print("  --- JSON ---")
    print(config.export("json"))

    print("  --- YAML ---")
    print(config.export("yaml"))

    print("  --- TOML ---")
    print(config.export("toml"))


# ---------------------------------------------------------------------------
# 10. Standalone validate() — post-hoc schema validation
# ---------------------------------------------------------------------------


def example_standalone_validate():
    """Load config without a schema, then validate after the fact."""
    print("\n" + "=" * 70)
    print("10. Standalone validate() — Post-Hoc Validation")
    print("=" * 70)

    try:
        from pydantic import BaseModel
    except ImportError:
        print("  (skipped — pydantic not installed)")
        return

    class ServerSchema(BaseModel):
        host: str
        port: int

    class AppConfig(BaseModel):
        server: ServerSchema

    data = {"server": {"host": "localhost", "port": 443}}

    config = Config(
        loaders=[DictLoader(data)],
    )

    is_valid = config.validate(schema=AppConfig)
    print(f"  Valid against AppConfig? {is_valid}")

    # Now try with bad data
    bad_data = {"server": {"host": "localhost", "port": "not-a-number"}}
    bad_config = Config(
        loaders=[DictLoader(bad_data)],
    )

    is_valid_bad = bad_config.validate(schema=AppConfig)
    print(f"  Valid with bad port?     {is_valid_bad}")


# ---------------------------------------------------------------------------
# 11. cs short alias — identical to config_stash
# ---------------------------------------------------------------------------


def example_cs_alias():
    """Demonstrate that 'cs' is a drop-in alias for 'config_stash'."""
    print("\n" + "=" * 70)
    print("11. cs Short Alias")
    print("=" * 70)

    # These two import styles are equivalent:
    from config_stash import Config as FullConfig
    from config_stash.loaders import YamlLoader as FullYaml
    from cs import Config as CsConfig
    from cs.loaders import YamlLoader as CsYaml

    print(f"  cs.Config is config_stash.Config           -> {CsConfig is FullConfig}")
    print(f"  cs.loaders.YamlLoader is ...YamlLoader     -> {CsYaml is FullYaml}")

    # Use the short alias to build a real config
    data = {"demo": {"alias": "works"}}
    config = CsConfig(
        loaders=[DictLoader(data)],
    )
    print(f"  demo.alias (via cs.Config) -> {config.demo.alias}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Run all extensibility examples."""
    print("=" * 70)
    print("Config-Stash Extensibility Examples")
    print("=" * 70)

    example_global_hook()
    example_key_hook()
    example_condition_hook()
    example_custom_loader()
    example_observability()
    example_event_emission()
    example_composition_include()
    example_composition_defaults()
    example_export()
    example_standalone_validate()
    example_cs_alias()

    print("\n" + "=" * 70)
    print("All extensibility examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
