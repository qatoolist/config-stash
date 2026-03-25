"""Loader manager for orchestrating multiple configuration loaders.

This module provides the ``LoaderManager`` class, which is responsible for
coordinating the execution of one or more configuration loaders, collecting
their results, and discovering loader plugins installed via Python entry points.

Use ``LoaderManager`` when you need to aggregate configuration data from several
sources (files, environment variables, remote endpoints) into a single ordered
list of ``(config_dict, source_name)`` tuples that can later be merged.

Example:
    >>> from config_stash.loaders.json_loader import JsonLoader
    >>> loaders = [JsonLoader("app.json"), JsonLoader("overrides.json")]
    >>> manager = LoaderManager(loaders)
    >>> manager._load_configs()
    >>> for cfg, source in manager.get_configs():
    ...     print(source, list(cfg.keys()))
"""

import importlib.metadata
from typing import Any, Dict, List, Tuple


class LoaderManager:
    """Orchestrates multiple configuration loaders and collects their output.

    ``LoaderManager`` iterates over a sequence of loader instances, invokes each
    one, and stores the successfully loaded configuration dictionaries alongside
    their source identifiers.  Loaders that raise exceptions are logged and
    skipped so that a single failing source does not prevent the remaining
    sources from being loaded.

    Attributes:
        loaders: An ordered sequence of loader instances.  Each loader must
            expose a ``load()`` method that returns a dictionary (or ``None``)
            and a ``source`` attribute that identifies where the configuration
            came from.
        configs: A list of ``(config_dict, source_name)`` tuples populated
            after ``_load_configs`` has been called.

    Example:
        >>> from config_stash.loaders.yaml_loader import YamlLoader
        >>> manager = LoaderManager([YamlLoader("base.yaml")])
        >>> manager._load_configs()
        >>> manager.get_configs()
        [({'db_host': 'localhost'}, 'base.yaml')]
    """

    def __init__(self, loaders: List[Any]) -> None:
        """Initialise the loader manager with an ordered list of loaders.

        Args:
            loaders: An iterable of loader instances.  Each loader must
                implement a ``load()`` method returning a ``dict`` or ``None``
                and expose a ``source`` attribute describing its origin
                (e.g. a file path or URL).

        Example:
            >>> from config_stash.loaders.json_loader import JsonLoader
            >>> manager = LoaderManager([JsonLoader("settings.json")])
        """
        self.loaders = loaders
        self.configs: List[Tuple[Dict[str, Any], str]] = []

    def _load_configs(self) -> None:
        """Execute every registered loader and collect successful results.

        Iterates over ``self.loaders`` in order, calling ``loader.load()`` on
        each one.  If a loader returns a non-``None`` dictionary it is appended
        to ``self.configs`` as a ``(config_dict, source)`` tuple.  If a loader
        raises an exception, a warning is logged and processing continues with
        the next loader.

        This method is idempotent in the sense that calling it multiple times
        will *append* additional results to ``self.configs``; reset ``configs``
        to an empty list beforehand if you need a fresh load.

        Raises:
            No exceptions are raised directly.  Individual loader failures are
            caught, logged at WARNING level, and skipped.

        Example:
            >>> manager = LoaderManager(loaders)
            >>> manager._load_configs()
            >>> len(manager.configs)  # one entry per successful loader
            2
        """
        import logging

        logger = logging.getLogger(__name__)
        for loader in self.loaders:
            try:
                config = loader.load()
                if config is not None:  # Only append if config was loaded successfully
                    self.configs.append((config, loader.source))
            except Exception as e:
                # Log warning but continue with other loaders
                logger.warning(f"Failed to load configuration from {loader.source}: {e}")
                continue

    def get_configs(self) -> List[Tuple[Dict[str, Any], str]]:
        """Return the list of loaded configuration tuples.

        Returns:
            A list of ``(config_dict, source)`` tuples in the same order as
            the loaders that produced them.  Each ``config_dict`` is the
            dictionary returned by the loader's ``load()`` method, and
            ``source`` is the string identifying the loader's origin.

        Example:
            >>> configs = manager.get_configs()
            >>> for cfg, src in configs:
            ...     print(f"{src}: {len(cfg)} keys")
        """
        return self.configs

    @staticmethod
    def load_plugins() -> Dict[str, Any]:
        """Discover and load configuration-loader plugins via entry points.

        Scans the ``config_stash.loaders`` entry-point group for installed
        packages that expose custom loader classes.  This allows third-party
        packages to register new configuration backends (e.g. a Consul or etcd
        loader) simply by declaring an entry point in their ``setup.cfg`` or
        ``pyproject.toml``.

        The method is compatible with both Python 3.10+ (which supports the
        ``group`` keyword in ``entry_points()``) and older Python versions.

        Returns:
            A dictionary mapping plugin names (strings) to their loaded
            classes or callables.

        Raises:
            No exceptions are raised directly.  Import errors within individual
            entry points will propagate from ``entry_point.load()``.

        Example:
            >>> plugins = LoaderManager.load_plugins()
            >>> plugins
            {'consul': <class 'my_plugin.ConsulLoader'>}
        """
        loaders = {}
        # Python 3.10+ uses select() method, older versions use dict-like access
        try:
            eps = importlib.metadata.entry_points(group="config_stash.loaders")
        except TypeError:
            # Python < 3.10
            eps = importlib.metadata.entry_points().get("config_stash.loaders", [])  # type: ignore[reportAttributeAccessIssue]

        for entry_point in eps:
            loaders[entry_point.name] = entry_point.load()
        return loaders
