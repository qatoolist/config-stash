"""Command-line interface for Config-Stash.

This module provides the CLI commands for Config-Stash, including
configuration loading, validation, export, debugging, and migration tools.
"""

import shutil
from pathlib import Path
from typing import Any, List, Tuple

try:
    import click
except ImportError:
    raise ImportError(
        "click is required for the CLI. " "Install with: pip install config-stash[cli]"
    )

from config_stash.config import Config
from config_stash.plugin_loader import get_loader


def parse_loader_specs(loader_specs: Tuple[str, ...]) -> List[Any]:
    """Parse loader specifications and return loader instances.

    Args:
        loader_specs: Tuple of specs in format "type:source"

    Returns:
        List of instantiated loader objects

    Raises:
        click.BadParameter: If loader spec format is invalid
    """
    loaders = []
    for spec in loader_specs:
        try:
            loader_type, source = spec.split(":", 1)
        except ValueError:
            raise click.BadParameter(
                f"Invalid loader spec '{spec}'. Expected format: 'type:source'"
            )

        try:
            LoaderClass = get_loader(loader_type)
        except ValueError as e:
            raise click.BadParameter(f"Unknown loader type '{loader_type}': {e}")

        loaders.append(LoaderClass(source))

    return loaders


def create_config(
    env: str,
    loader_specs: Tuple[str, ...],
    dynamic_reloading: bool,
    use_env_expander: bool,
    use_type_casting: bool,
) -> Config:
    """Create a Config instance with parsed loaders.

    Args:
        env: Environment name
        loader_specs: Tuple of loader specifications
        dynamic_reloading: Enable file watching
        use_env_expander: Enable environment variable expansion
        use_type_casting: Enable automatic type casting

    Returns:
        Configured Config instance
    """
    loaders = parse_loader_specs(loader_specs)
    return Config(
        env=env,
        loaders=loaders if loaders else None,
        dynamic_reloading=dynamic_reloading,
        use_env_expander=use_env_expander,
        use_type_casting=use_type_casting,
    )


def _parse_override_value(value: str) -> Any:
    """Parse override value, inferring type from string representation.

    Args:
        value: String value to parse

    Returns:
        Parsed value with appropriate type (int, float, bool, or str)

    Example:
        >>> _parse_override_value("42")
        42
        >>> _parse_override_value("3.14")
        3.14
        >>> _parse_override_value("true")
        True
        >>> _parse_override_value("hello")
        'hello'
    """
    from config_stash.utils.type_coercion import parse_scalar_value

    return parse_scalar_value(value.strip(), extended_booleans=True)


def get_examples_info():
    """Get information about available examples.

    Returns:
        Dict mapping example names to their descriptions
    """
    # Get the package directory
    package_dir = Path(__file__).parent.parent.parent
    examples_dir = package_dir / "examples"

    examples = {
        "working_demo.py": {
            "description": "Comprehensive demo of core Config-Stash features",
            "topics": ["loading", "environments", "export", "diff", "validation"],
        },
        "advanced_features.py": {
            "description": "Advanced features including validation and remote loading",
            "topics": ["schema", "pydantic", "remote", "composition"],
        },
        "simple_demo.py": {
            "description": "Simple example showing basic configuration usage",
            "topics": ["basic", "loading", "access"],
        },
        "quick_demo.py": {
            "description": "Quick start example with common use cases",
            "topics": ["quickstart", "overview"],
        },
    }

    # Only return examples that actually exist
    available_examples = {}
    if examples_dir.exists():
        for name, info in examples.items():
            if (examples_dir / name).exists():
                available_examples[name] = info

    return available_examples


@click.group()
def cli():
    """Config-Stash CLI - Configuration management made easy"""
    pass


@cli.command()
@click.argument("env")
@click.option(
    "--loader",
    "loader_specs",
    multiple=True,
    help='Loader spec in format "type:source"',
)
@click.option(
    "--override",
    "overrides",
    multiple=True,
    help='Override configuration values in format "key=value" (e.g., "database.host=localhost")',
)
@click.option(
    "--dynamic-reloading",
    is_flag=True,
    default=False,
    help="Enable dynamic reloading of configurations",
)
@click.option(
    "--use-env-expander/--no-use-env-expander",
    default=True,
    help="Enable/disable environment variable expansion",
)
@click.option(
    "--use-type-casting/--no-use-type-casting",
    default=True,
    help="Enable/disable automatic type casting",
)
def load(
    env, loader_specs, overrides, dynamic_reloading, use_env_expander, use_type_casting
):
    """Load and display the merged configuration.

    This command loads configuration from specified sources and displays
    the merged result. Optional overrides can be applied via --override flags.

    Args:
        env: Environment name (e.g., "production", "development")
        loader_specs: Tuple of loader specifications in format "type:source"
        overrides: Tuple of override specifications in format "key=value"
        dynamic_reloading: Enable file watching for automatic reloading
        use_env_expander: Enable environment variable expansion in config values
        use_type_casting: Enable automatic type casting

    Example:
        >>> # Basic usage
        >>> config-stash load production --loader yaml:config.yaml

        >>> # With overrides
        >>> config-stash load production --loader yaml:config.yaml \\
        ...     --override "database.host=remote.db.example.com" \\
        ...     --override "database.port=3306"
    """
    try:
        config = create_config(
            env, loader_specs, dynamic_reloading, use_env_expander, use_type_casting
        )

        # Apply overrides if provided
        if overrides:
            for override_spec in overrides:
                try:
                    key, value = override_spec.split("=", 1)
                    # Try to infer type from value
                    parsed_value = _parse_override_value(value)
                    config.set(key.strip(), parsed_value, override=True)
                except ValueError:
                    click.echo(
                        f"Warning: Invalid override format '{override_spec}'. Expected 'key=value'",
                        err=True,
                    )

        click.echo(config.merged_config)
    except click.BadParameter as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@cli.command()
@click.argument("env")
@click.argument("key")
@click.option(
    "--loader",
    "loader_specs",
    multiple=True,
    help='Loader spec in format "type:source"',
)
@click.option(
    "--dynamic-reloading",
    is_flag=True,
    default=False,
    help="Enable dynamic reloading of configurations",
)
@click.option(
    "--use-env-expander/--no-use-env-expander",
    default=True,
    help="Enable/disable environment variable expansion",
)
@click.option(
    "--use-type-casting/--no-use-type-casting",
    default=True,
    help="Enable/disable automatic type casting",
)
def get(env, key, loader_specs, dynamic_reloading, use_env_expander, use_type_casting):
    """Get the value of a configuration key.

    This command loads configuration and retrieves a specific key's value.
    Supports nested keys using dot notation (e.g., "database.host").

    Args:
        env: Environment name
        key: Configuration key to retrieve (supports dot notation for nested keys)
        loader_specs: Tuple of loader specifications in format "type:source"
        dynamic_reloading: Enable file watching
        use_env_expander: Enable environment variable expansion
        use_type_casting: Enable automatic type casting

    Example:
        >>> config-stash get production database.host --loader yaml:config.yaml
    """
    try:
        config = create_config(
            env, loader_specs, dynamic_reloading, use_env_expander, use_type_casting
        )
        value = getattr(config, key)

        # Convert AttributeAccessor or dict to dict for proper display
        if hasattr(value, "lazy_loader") and hasattr(value.lazy_loader, "config"):
            # It's an AttributeAccessor, get the underlying dict
            import json

            click.echo(json.dumps(value.lazy_loader.config, indent=2))
        elif isinstance(value, dict):
            import json

            click.echo(json.dumps(value, indent=2))
        else:
            click.echo(value)
    except click.BadParameter as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except AttributeError:
        click.echo(f"Error: Configuration key '{key}' not found", err=True)
        raise SystemExit(1)


@cli.command()
@click.argument("env")
@click.option(
    "--loader",
    "loader_specs",
    multiple=True,
    help='Loader spec in format "type:source"',
)
@click.option("--schema", help="Path to schema file for validation")
@click.option(
    "--fix", is_flag=True, help="Attempt to auto-fix common validation issues"
)
def validate(env, loader_specs, schema, fix):
    """Validate configuration against a schema.

    This command validates the loaded configuration against a provided schema
    (JSON Schema file). Optionally attempts to auto-fix common issues.

    Args:
        env: Environment name
        loader_specs: Tuple of loader specifications in format "type:source"
        schema: Path to JSON Schema file for validation
        fix: Attempt to auto-fix common validation issues (not yet implemented)

    Example:
        >>> config-stash validate production --loader yaml:config.yaml --schema schema.json
    """
    try:
        config = create_config(env, loader_specs, False, True, True)

        # Check if configuration is empty (all loaders failed)
        if not config.merged_config or config.merged_config == {}:
            click.echo(
                "Error: No configuration could be loaded. Check that your config files exist.",
                err=True,
            )
            raise SystemExit(1)

        # Load schema if provided
        schema_dict = None
        if schema:
            import json

            with open(schema, "r") as f:
                schema_dict = json.load(f)

        is_valid = config.validate(schema_dict)

        if is_valid:
            click.echo(click.style("✓ Configuration is valid", fg="green"))
        else:
            if fix:
                click.echo(
                    "Auto-fix is not yet implemented. Please fix validation errors manually."
                )
            click.echo(click.style("✗ Configuration is invalid", fg="red"), err=True)
            raise SystemExit(1)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@cli.command()
@click.argument("env")
@click.option(
    "--loader",
    "loader_specs",
    multiple=True,
    help='Loader spec in format "type:source"',
)
@click.option(
    "--format",
    type=click.Choice(["json", "yaml", "toml"]),
    default="json",
    help="Export format",
)
@click.option("--output", "-o", help="Output file path")
def export(env, loader_specs, format, output):
    """Export configuration in different formats.

    This command exports the loaded configuration to a file in the specified
    format (JSON, YAML, or TOML). If no output file is specified, prints to stdout.

    Args:
        env: Environment name
        loader_specs: Tuple of loader specifications in format "type:source"
        format: Export format (json, yaml, or toml)
        output: Output file path (optional, defaults to stdout)

    Example:
        >>> config-stash export production --loader yaml:config.yaml --format=json --output=config.json
    """
    try:
        config = create_config(env, loader_specs, False, True, True)
        exported = config.export(format=format, output_path=output)

        if not output:
            click.echo(exported)
        else:
            click.echo(f"✓ Configuration exported to {output}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@cli.command()
@click.argument("env")
@click.option(
    "--loader",
    "loader_specs",
    multiple=True,
    help='Loader spec in format "type:source"',
)
@click.option("--key", help="Debug specific configuration key")
@click.option("--export-report", help="Export debug report to file")
def debug(env, loader_specs, key, export_report):
    """Debug configuration sources and overrides.

    This command provides detailed debugging information about configuration
    sources, overrides, and value resolution. Can focus on a specific key
    or export a full debug report.

    Args:
        env: Environment name
        loader_specs: Tuple of loader specifications in format "type:source"
        key: Optional configuration key to debug (if not provided, shows general info)
        export_report: Optional path to export debug report JSON file

    Example:
        >>> config-stash debug production --key=database.host --loader yaml:config.yaml
        >>> config-stash debug production --export-report=debug.json
    """
    try:
        # Create config with debug mode enabled
        loaders = parse_loader_specs(loader_specs) if loader_specs else None
        config = Config(
            env=env, loaders=loaders, debug_mode=True, enable_ide_support=False
        )

        if export_report:
            config.export_debug_report(export_report)
            click.echo(f"✓ Debug report exported to {export_report}")
        elif key:
            # Debug specific key
            info = config.get_source_info(key)
            if info:
                click.echo(f"\n{info}")

                # Show override history
                history = config.get_override_history(key)
                if history:
                    click.echo("\nOverride History:")
                    for i, h in enumerate(history, 1):
                        click.echo(f"  {i}. {h.source_file}: {h.value}")
            else:
                click.echo(f"No source information found for key: {key}")
        else:
            # Show general debug info
            config.print_debug_info()

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@cli.command()
@click.argument("env")
@click.option(
    "--loader",
    "loader_specs",
    multiple=True,
    help='Loader spec in format "type:source"',
)
@click.option("--fix", is_flag=True, help="Attempt to auto-fix linting issues")
@click.option("--strict", is_flag=True, help="Use strict linting rules")
def lint(env, loader_specs, fix, strict):
    """Lint configuration files for best practices and common issues.

    This command checks the configuration for common issues, deprecated keys,
    and best practices violations. Can optionally attempt to auto-fix issues.

    Args:
        env: Environment name
        loader_specs: Tuple of loader specifications in format "type:source"
        fix: Attempt to auto-fix linting issues (not yet implemented)
        strict: Use strict linting rules and exit with error code if issues found

    Example:
        >>> config-stash lint production --loader yaml:config.yaml
        >>> config-stash lint production --loader yaml:config.yaml --strict
    """
    try:
        config = create_config(env, loader_specs, False, True, True)

        issues = []
        warnings = []

        # Check for common issues
        config_dict = config.to_dict()

        # Check for deprecated keys
        deprecated_keys = ["_old_key", "_legacy"]  # Example
        for key in config.keys():
            if any(dep in key for dep in deprecated_keys):
                issues.append(f"Deprecated key detected: {key}")

        # Check for missing required keys (basic check)
        if not config_dict:
            warnings.append("Configuration is empty")

        # Check for nested structure issues
        for key in config.keys():
            try:
                value = config.get(key)
                if value is None:
                    warnings.append(f"Key '{key}' has None value")
            except Exception:
                pass

        # Report issues
        if issues or warnings:
            if issues:
                click.echo(click.style("\n✗ Issues found:", fg="red", bold=True))
                for issue in issues:
                    click.echo(f"  • {issue}")

            if warnings:
                click.echo(click.style("\n⚠ Warnings:", fg="yellow"))
                for warning in warnings:
                    click.echo(f"  • {warning}")

            if fix:
                click.echo("\nAuto-fix is not yet implemented.")
            click.echo(f"\nTotal: {len(issues)} issue(s), {len(warnings)} warning(s)")
            if strict and issues:
                raise SystemExit(1)
        else:
            click.echo(click.style("✓ Configuration passed linting checks", fg="green"))

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@cli.command()
@click.argument(
    "source_format",
    type=click.Choice(["dynaconf", "hydra", "omegaconf", "dotenv", "env"]),
)
@click.argument("config_file", type=click.Path(exists=True))
@click.option("--output", "-o", help="Output file path (default: stdout)")
@click.option(
    "--target-format",
    type=click.Choice(["yaml", "json", "toml"]),
    default="yaml",
    help="Target format",
)
def migrate(source_format, config_file, output, target_format):
    """Migrate configuration from other tools to Config-Stash format.

    This command helps migrate configurations from other tools (python-dotenv,
    Dynaconf, Hydra) to Config-Stash format. Preserves configuration values
    and converts format syntax where needed.

    Args:
        source_format: Source format (dotenv, env, dynaconf, or hydra)
        config_file: Path to the source configuration file
        output: Output file path (optional, defaults to stdout)
        target_format: Target format for output (yaml, json, or toml)

    Example:
        >>> config-stash migrate dotenv .env --output config.yaml
        >>> config-stash migrate dynaconf settings.yaml --output config.yaml
    """
    try:
        import json

        import yaml

        migrated_config = {}

        if source_format == "dotenv" or source_format == "env":
            # Migrate .env file
            with open(config_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        # Convert nested keys (APP_DATABASE__HOST -> database.host)
                        if "__" in key:
                            parts = key.split("__")
                            current = migrated_config
                            for part in parts[:-1]:
                                part = part.lower().replace("_", " ")
                                part = "".join(
                                    word.capitalize() for word in part.split()
                                )
                                if part.lower() not in current:
                                    current[part.lower()] = {}
                                current = current[part.lower()]
                            current[parts[-1].lower()] = value
                        else:
                            migrated_config[key.lower()] = value

        elif source_format == "dynaconf":
            # Try to parse as YAML/JSON/TOML first
            with open(config_file, "r") as f:
                content = f.read()
                try:
                    migrated_config = yaml.safe_load(content) or {}
                except Exception:
                    try:
                        migrated_config = json.loads(content) or {}
                    except Exception:
                        click.echo(
                            f"Warning: Could not parse {config_file} as YAML or JSON",
                            err=True,
                        )

        elif source_format == "omegaconf":
            # OmegaConf configs are YAML, possibly with ${interpolation}
            with open(config_file, "r") as f:
                content = f.read()
                config = yaml.safe_load(content) or {}
                # Warn about interpolation patterns
                import re

                interpolations = re.findall(r"\$\{[^}]+\}", content)
                if interpolations:
                    click.echo(
                        f"Warning: Found {len(interpolations)} OmegaConf "
                        f"interpolation(s) that need manual conversion: "
                        f"{interpolations[:3]}{'...' if len(interpolations) > 3 else ''}",
                        err=True,
                    )
                migrated_config = config

        elif source_format == "hydra":
            # Hydra configs are usually YAML with defaults list
            with open(config_file, "r") as f:
                config = yaml.safe_load(f) or {}
                # Remove Hydra-specific keys
                config.pop("defaults", None)
                config.pop("hydra", None)
                migrated_config = config

        # Output migrated config
        if target_format == "yaml":
            output_str = yaml.dump(migrated_config, default_flow_style=False)
        elif target_format == "json":
            output_str = json.dumps(migrated_config, indent=2)
        else:  # toml
            from config_stash.utils.toml_compat import dumps as toml_dumps

            output_str = toml_dumps(migrated_config)

        if output:
            with open(output, "w") as f:
                f.write(output_str)
            click.echo(click.style(f"✓ Configuration migrated to {output}", fg="green"))
        else:
            click.echo(output_str)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@cli.command()
@click.argument("env")
@click.option(
    "--loader",
    "loader_specs",
    multiple=True,
    help='Loader spec in format "type:source"',
)
@click.option("--key", help="Explain specific configuration key")
def explain(env, loader_specs, key):
    """Explain how configuration values were resolved.

    This command provides detailed information about how a specific
    configuration key was resolved, including source files and override history.

    Args:
        env: Environment name
        loader_specs: Tuple of loader specifications in format "type:source"
        key: Configuration key to explain (supports dot notation)

    Example:
        >>> config-stash explain production --key=database.host --loader yaml:config.yaml
    """
    try:
        loaders = parse_loader_specs(loader_specs) if loader_specs else None
        config = Config(
            env=env, loaders=loaders, debug_mode=True, enable_ide_support=False
        )

        if key:
            info = config.explain(key)
            import json

            click.echo(json.dumps(info, indent=2))
        else:
            click.echo("Please specify a key with --key to explain")
            click.echo("Example: config-stash explain production --key=database.host")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@cli.command()
@click.argument("env")
@click.option(
    "--loader",
    "loader_specs",
    multiple=True,
    help='Loader spec in format "type:source"',
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["markdown", "json"]),
    default="markdown",
    help="Documentation output format",
)
@click.option("--output", "-o", help="Output file path")
def docs(env, loader_specs, fmt, output):
    """Generate configuration documentation.

    This command loads configuration from specified sources and generates
    a reference document listing all keys, types, current values, and sources.

    Args:
        env: Environment name (e.g., "production", "development")
        loader_specs: Tuple of loader specifications in format "type:source"
        fmt: Output format (markdown or json)
        output: Output file path (optional, defaults to stdout)

    Example:
        >>> config-stash docs production --loader yaml:config.yaml --format markdown
        >>> config-stash docs production --loader yaml:config.yaml --format json --output config-reference.md
    """
    try:
        config = create_config(env, loader_specs, False, True, True)
        docs_output = config.generate_docs(format=fmt)

        if output:
            with open(output, "w") as f:
                f.write(docs_output)
            click.echo(f"Documentation written to {output}")
        else:
            click.echo(docs_output)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@cli.command()
@click.argument("env1")
@click.argument("env2")
@click.option(
    "--loader1", "loader_specs1", multiple=True, help="Loaders for first config"
)
@click.option(
    "--loader2", "loader_specs2", multiple=True, help="Loaders for second config"
)
@click.option(
    "--format",
    type=click.Choice(["json", "yaml", "unified"]),
    default="unified",
    help="Diff format",
)
def diff(env1, env2, loader_specs1, loader_specs2, format):
    """Compare two configurations.

    This command compares two configurations and shows the differences
    between them. Useful for comparing different environments or versions.

    Args:
        env1: First environment name
        env2: Second environment name
        loader_specs1: Loader specifications for first configuration
        loader_specs2: Loader specifications for second configuration
        format: Output format (json, yaml, or unified text)

    Example:
        >>> config-stash diff development production \\
        ...     --loader1 yaml:dev.yaml --loader2 yaml:prod.yaml
    """
    try:
        loaders1 = parse_loader_specs(loader_specs1) if loader_specs1 else None
        loaders2 = parse_loader_specs(loader_specs2) if loader_specs2 else None

        config1 = Config(env=env1, loaders=loaders1, enable_ide_support=False)
        config2 = Config(env=env2, loaders=loaders2, enable_ide_support=False)

        dict1 = config1.to_dict()
        dict2 = config2.to_dict()

        # Simple diff implementation
        all_keys = set(config1.keys()) | set(config2.keys())
        differences = []

        for key in sorted(all_keys):
            val1 = config1.get(key, "__MISSING__")
            val2 = config2.get(key, "__MISSING__")
            if val1 != val2:
                differences.append({"key": key, "env1": val1, "env2": val2})

        if format == "unified":
            if differences:
                click.echo(f"\nDifferences between {env1} and {env2}:\n")
                for diff in differences:
                    click.echo(f"Key: {diff['key']}")
                    click.echo(f"  {env1}: {diff['env1']}")
                    click.echo(f"  {env2}: {diff['env2']}\n")
            else:
                click.echo(click.style("✓ Configurations are identical", fg="green"))
        else:
            import json

            click.echo(json.dumps(differences, indent=2))

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@cli.group()
def examples():
    """Manage and explore Config-Stash examples"""
    pass


@examples.command(name="list")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
def list_examples(verbose):
    """List all available examples"""
    examples_info = get_examples_info()

    if not examples_info:
        click.echo(
            "No examples found. Examples may not be installed with this package."
        )
        click.echo("Visit https://github.com/qatoolist/config-stash/tree/main/examples")
        return

    click.echo("🚀 Available Config-Stash Examples\n")
    click.echo("=" * 60)

    for name, info in examples_info.items():
        click.echo(f"\n📄 {click.style(name, fg='green', bold=True)}")
        click.echo(f"   {info['description']}")
        if verbose:
            click.echo(f"   Topics: {', '.join(info['topics'])}")

    click.echo("\n" + "=" * 60)
    click.echo("\nTo export an example, run:")
    click.echo("  config-stash examples export <name> [--output-dir <path>]")
    click.echo("\nTo export all examples:")
    click.echo("  config-stash examples export --all")


@examples.command(name="export")
@click.argument("name", required=False)
@click.option("--all", "export_all", is_flag=True, help="Export all examples")
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    help="Output directory (default: current directory)",
)
def export_examples(name, export_all, output_dir):
    """Export example(s) to your local directory"""
    examples_info = get_examples_info()

    if not examples_info:
        click.echo(
            "No examples found. Examples may not be installed with this package."
        )
        click.echo("Visit https://github.com/qatoolist/config-stash/tree/main/examples")
        return

    # Determine output directory
    output_path = Path(output_dir) if output_dir else Path.cwd()

    # Validate the output directory
    if not output_path.exists():
        try:
            output_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            click.echo(f"Error creating output directory: {e}", err=True)
            raise SystemExit(1)

    # Get package examples directory
    package_dir = Path(__file__).parent.parent.parent
    examples_dir = package_dir / "examples"

    # Determine which examples to export
    if export_all:
        to_export = list(examples_info.keys())
        click.echo(f"Exporting all {len(to_export)} examples...")
    elif name:
        if name not in examples_info:
            click.echo(f"Error: Example '{name}' not found.", err=True)
            click.echo("\nAvailable examples:")
            for example_name in examples_info:
                click.echo(f"  - {example_name}")
            raise SystemExit(1)
        to_export = [name]
    else:
        click.echo("Error: Please specify an example name or use --all", err=True)
        click.echo("\nAvailable examples:")
        for example_name, info in examples_info.items():
            click.echo(f"  - {example_name}: {info['description']}")
        raise SystemExit(1)

    # Export the examples
    exported = []
    for example_name in to_export:
        source_file = examples_dir / example_name
        dest_file = output_path / example_name

        # Check if file already exists
        if dest_file.exists():
            if not click.confirm(f"File {dest_file} already exists. Overwrite?"):
                click.echo(f"Skipped: {example_name}")
                continue

        try:
            shutil.copy2(source_file, dest_file)
            exported.append(example_name)
            click.echo(f"✅ Exported: {example_name} -> {dest_file}")
        except Exception as e:
            click.echo(f"❌ Failed to export {example_name}: {e}", err=True)

    # Summary
    if exported:
        click.echo(
            f"\n✨ Successfully exported {len(exported)} example(s) to {output_path}"
        )
        click.echo("\nTo run an example:")
        click.echo(f"  python {exported[0]}")
    else:
        click.echo("\n⚠️  No examples were exported.")


@examples.command(name="show")
@click.argument("name")
@click.option("--no-pager", is_flag=True, help="Don't use a pager for output")
def show_example(name, no_pager):
    """Display the source code of an example"""
    examples_info = get_examples_info()

    if not examples_info:
        click.echo(
            "No examples found. Examples may not be installed with this package."
        )
        return

    if name not in examples_info:
        click.echo(f"Error: Example '{name}' not found.", err=True)
        click.echo("\nAvailable examples:")
        for example_name in examples_info:
            click.echo(f"  - {example_name}")
        raise SystemExit(1)

    # Get the example file
    package_dir = Path(__file__).parent.parent.parent
    example_file = package_dir / "examples" / name

    try:
        content = example_file.read_text()

        # Add header
        header = f"""
{'=' * 60}
📄 {name}
{examples_info[name]['description']}
{'=' * 60}

"""
        full_content = header + content

        if no_pager:
            click.echo(full_content)
        else:
            click.echo_via_pager(full_content)

    except Exception as e:
        click.echo(f"Error reading example: {e}", err=True)
        raise SystemExit(1)


@examples.command(name="run")
@click.argument("name")
def run_example(name):
    """Run an example directly"""
    examples_info = get_examples_info()

    if not examples_info:
        click.echo(
            "No examples found. Examples may not be installed with this package."
        )
        return

    if name not in examples_info:
        click.echo(f"Error: Example '{name}' not found.", err=True)
        click.echo("\nAvailable examples:")
        for example_name in examples_info:
            click.echo(f"  - {example_name}")
        raise SystemExit(1)

    # Get the example file
    package_dir = Path(__file__).parent.parent.parent
    example_file = package_dir / "examples" / name

    click.echo(f"🚀 Running example: {name}\n")
    click.echo("=" * 60)

    # Run the example
    import subprocess
    import sys

    try:
        result = subprocess.run(
            [sys.executable, str(example_file)], capture_output=False, text=True
        )
        if result.returncode != 0:
            raise SystemExit(result.returncode)
    except KeyboardInterrupt:
        click.echo("\n\n⚠️  Example interrupted by user")
        raise SystemExit(1)
    except Exception as e:
        click.echo(f"\n❌ Error running example: {e}", err=True)
        raise SystemExit(1)


if __name__ == "__main__":
    cli()
