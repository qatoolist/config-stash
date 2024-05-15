import click
from config_stash.config import Config
from config_stash.plugin_loader import get_loader

@click.group()
def cli():
    """CLI tool for managing configurations"""
    pass

@cli.command()
@click.argument('env')
@click.option('--loader', 'loader_specs', multiple=True, help='Loader spec in format "type:source"')
@click.option('--dynamic-reloading', is_flag=True, default=False, help='Enable dynamic reloading of configurations')
@click.option('--use-env-expander', is_flag=True, default=True, help='Enable environment variable expansion')
@click.option('--use-type-casting', is_flag=True, default=True, help='Enable automatic type casting')
def load(env, loader_specs, dynamic_reloading, use_env_expander, use_type_casting):
    """Load and display the merged configuration"""
    loaders = []

    for spec in loader_specs:
        loader_type, source = spec.split(':', 1)
        LoaderClass = get_loader(loader_type)
        loaders.append(LoaderClass(source))

    config = Config(
        env=env,
        loaders=loaders,
        dynamic_reloading=dynamic_reloading,
        use_env_expander=use_env_expander,
        use_type_casting=use_type_casting
    )
    click.echo(config.merged_config)

@cli.command()
@click.argument('env')
@click.argument('key')
@click.option('--loader', 'loader_specs', multiple=True, help='Loader spec in format "type:source"')
@click.option('--dynamic-reloading', is_flag=True, default=False, help='Enable dynamic reloading of configurations')
@click.option('--use-env-expander', is_flag=True, default=True, help='Enable environment variable expansion')
@click.option('--use-type-casting', is_flag=True, default=True, help='Enable automatic type casting')
def get(env, key, loader_specs, dynamic_reloading, use_env_expander, use_type_casting):
    """Get the value of a configuration key"""
    loaders = []

    for spec in loader_specs:
        loader_type, source = spec.split(':', 1)
        LoaderClass = get_loader(loader_type)
        loaders.append(LoaderClass(source))

    config = Config(
        env=env,
        loaders=loaders,
        dynamic_reloading=dynamic_reloading,
        use_env_expander=use_env_expander,
        use_type_casting=use_type_casting
    )
    value = config.__getattr__(key)
    click.echo(value)

if __name__ == '__main__':
    cli()