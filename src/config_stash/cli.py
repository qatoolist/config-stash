import shutil
from pathlib import Path
from typing import Any, List, Tuple

import click

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
@click.option("--loader", "loader_specs", multiple=True, help='Loader spec in format "type:source"')
@click.option(
    "--dynamic-reloading",
    is_flag=True,
    default=False,
    help="Enable dynamic reloading of configurations",
)
@click.option(
    "--use-env-expander", is_flag=True, default=True, help="Enable environment variable expansion"
)
@click.option(
    "--use-type-casting", is_flag=True, default=True, help="Enable automatic type casting"
)
def load(env, loader_specs, dynamic_reloading, use_env_expander, use_type_casting):
    """Load and display the merged configuration"""
    try:
        config = create_config(
            env, loader_specs, dynamic_reloading, use_env_expander, use_type_casting
        )
        click.echo(config.merged_config)
    except click.BadParameter as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@cli.command()
@click.argument("env")
@click.argument("key")
@click.option("--loader", "loader_specs", multiple=True, help='Loader spec in format "type:source"')
@click.option(
    "--dynamic-reloading",
    is_flag=True,
    default=False,
    help="Enable dynamic reloading of configurations",
)
@click.option(
    "--use-env-expander", is_flag=True, default=True, help="Enable environment variable expansion"
)
@click.option(
    "--use-type-casting", is_flag=True, default=True, help="Enable automatic type casting"
)
def get(env, key, loader_specs, dynamic_reloading, use_env_expander, use_type_casting):
    """Get the value of a configuration key"""
    try:
        config = create_config(
            env, loader_specs, dynamic_reloading, use_env_expander, use_type_casting
        )
        value = getattr(config, key)
        click.echo(value)
    except click.BadParameter as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except AttributeError:
        click.echo(f"Error: Configuration key '{key}' not found", err=True)
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
        click.echo("No examples found. Examples may not be installed with this package.")
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
    "--output-dir", "-o", type=click.Path(), help="Output directory (default: current directory)"
)
def export_examples(name, export_all, output_dir):
    """Export example(s) to your local directory"""
    examples_info = get_examples_info()

    if not examples_info:
        click.echo("No examples found. Examples may not be installed with this package.")
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
        click.echo(f"\n✨ Successfully exported {len(exported)} example(s) to {output_path}")
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
        click.echo("No examples found. Examples may not be installed with this package.")
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
        click.echo("No examples found. Examples may not be installed with this package.")
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
