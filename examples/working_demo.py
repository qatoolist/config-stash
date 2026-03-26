#!/usr/bin/env python3
"""Working demonstration of Config-Stash core features."""

import json
import tempfile
from pathlib import Path

from config_stash import Config
from config_stash.exporters import ConfigExporter, add_export_methods
from config_stash.loaders.json_loader import JsonLoader


def main():
    """Run the working demo with features that are confirmed to work."""
    print("🚀 Config-Stash Working Demo\n")
    print("=" * 60)

    # Create a comprehensive JSON config that works
    json_content = {
        "development": {
            "app": {"name": "MyApplication", "version": "1.0.0", "debug": True},
            "database": {
                "host": "localhost",
                "port": 5432,
                "username": "dev_user",
                "password": "dev_pass",
                "pool_size": 10,
            },
            "api": {
                "base_url": "http://localhost:8000",
                "timeout": 30,
                "retry_count": 3,
            },
            "features": {"logging": True, "metrics": False, "cache": True},
        },
        "production": {
            "app": {"name": "MyApplication", "version": "1.0.0", "debug": False},
            "database": {
                "host": "prod-db.example.com",
                "port": 5432,
                "username": "prod_user",
                "password": "prod_pass",
                "pool_size": 50,
                "ssl": True,
            },
            "api": {
                "base_url": "https://api.example.com",
                "timeout": 60,
                "retry_count": 5,
                "rate_limit": 1000,
            },
            "features": {
                "logging": True,
                "metrics": True,
                "cache": True,
                "monitoring": True,
            },
        },
    }

    # Create temp file
    json_file = Path(tempfile.gettempdir()) / "demo_config.json"
    json_file.write_text(json.dumps(json_content, indent=2))

    print(f"📁 Created config file: {json_file}")
    print()

    # 1. Load Development Configuration
    print("1️⃣ Development Configuration")
    print("-" * 40)

    dev_config = Config(env="development", loaders=[JsonLoader(str(json_file))])

    print(f"App Name: {dev_config.app.name}")
    print(f"Debug Mode: {dev_config.app.debug}")
    print(f"Database Host: {dev_config.database.host}")
    print(f"API URL: {dev_config.api.base_url}")
    print(f"Features - Logging: {dev_config.features.logging}")
    print(f"Features - Metrics: {dev_config.features.metrics}")
    print()

    # 2. Load Production Configuration
    print("2️⃣ Production Configuration")
    print("-" * 40)

    prod_config = Config(env="production", loaders=[JsonLoader(str(json_file))])

    print(f"App Name: {prod_config.app.name}")
    print(f"Debug Mode: {prod_config.app.debug}")
    print(f"Database Host: {prod_config.database.host}")
    print(f"Database SSL: {getattr(prod_config.database, 'ssl', False)}")
    print(f"API URL: {prod_config.api.base_url}")
    print(f"API Rate Limit: {getattr(prod_config.api, 'rate_limit', 'N/A')}")
    print(f"Features - Metrics: {prod_config.features.metrics}")
    print(
        f"Features - Monitoring: {getattr(prod_config.features, 'monitoring', False)}"
    )
    print()

    # 3. Export Configuration
    print("3️⃣ Export Configuration")
    print("-" * 40)

    # Add export methods
    add_export_methods(Config)

    # Export as JSON
    print("JSON Export (first 200 chars):")
    json_export = prod_config.to_json(indent=2)
    print(json_export[:200] + "...")
    print()

    # Export as YAML
    print("YAML Export (first 200 chars):")
    yaml_export = prod_config.to_yaml()
    print(yaml_export[:200] + "...")
    print()

    # Export as Environment Variables
    print("Environment Variables (first 10 lines):")
    env_export = prod_config.to_env(prefix="APP")
    lines = env_export.split("\n")
    for line in lines[:10]:
        print(f"  {line}")
    if len(lines) > 10:
        print(f"  ... ({len(lines) - 10} more lines)")
    print()

    # 4. Configuration as Dictionary
    print("4️⃣ Configuration as Dictionary")
    print("-" * 40)

    config_dict = prod_config.to_dict()
    print(f"Config keys: {list(config_dict.keys())}")
    print(f"Database config: {config_dict['database']}")
    print()

    # 5. Compare Development and Production
    print("5️⃣ Configuration Diff (Dev vs Prod)")
    print("-" * 40)

    diff = ConfigExporter.diff(dev_config, prod_config, format="json")
    diff_dict = json.loads(diff)

    print("Key differences:")
    for key, value in diff_dict.items():
        if key.startswith("~"):
            print(f"  Modified: {key}")
            if isinstance(value, dict) and "old" in value and "new" in value:
                print(f"    Old: {value['old']}")
                print(f"    New: {value['new']}")
        elif key.startswith("+"):
            print(f"  Added in prod: {key} = {value}")
        elif key.startswith("-"):
            print(f"  Removed in prod: {key} = {value}")
    print()

    # 6. Save Configuration to Different Formats
    print("6️⃣ Save Configuration to Files")
    print("-" * 40)

    output_dir = Path(tempfile.gettempdir()) / "config_output"
    output_dir.mkdir(exist_ok=True)

    # Save in different formats
    prod_config.dump(str(output_dir / "config.json"))
    prod_config.dump(str(output_dir / "config.yaml"))
    prod_config.dump(str(output_dir / "config.toml"))
    prod_config.dump(str(output_dir / ".env"), format="env")

    print(f"Saved configurations to {output_dir}:")
    for file in output_dir.iterdir():
        print(f"  - {file.name}")
    print()

    # Cleanup
    json_file.unlink()
    for file in output_dir.iterdir():
        file.unlink()
    output_dir.rmdir()

    print("=" * 60)
    print("✨ Demo Complete!")
    print("\n📚 Key Features Demonstrated:")
    print("  ✅ Environment-specific configurations")
    print("  ✅ Attribute-style access to nested configs")
    print("  ✅ Export to JSON, YAML, TOML, ENV formats")
    print("  ✅ Configuration comparison (diff)")
    print("  ✅ Save configurations to files")
    print("\n🚀 Additional Features Available:")
    print("  • Schema validation (JSON Schema)")
    print("  • Type validation (Pydantic)")
    print("  • Remote loading (HTTP, S3, Git)")
    print("  • Dynamic reloading")
    print("  • Configuration hooks")
    print("  • Thread-safe operations")
    print("\n📖 See README.md for complete documentation")


if __name__ == "__main__":
    main()
