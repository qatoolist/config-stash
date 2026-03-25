"""Source tracking for configuration keys.

This module provides the ``SourceTracker`` class, which determines which
configuration source (file, environment, remote endpoint, etc.) is responsible
for a given key's current value.  This is especially useful for debugging
configuration precedence issues when multiple sources contribute overlapping
keys.

Example:
    >>> from config_stash.source_tracker import SourceTracker
    >>> tracker = SourceTracker(loaders)
    >>> tracker.get_source("database.host")
    'production.yaml'
"""


class SourceTracker:
    """Tracks which loader supplied the winning value for each configuration key.

    When configuration is assembled from multiple sources, later sources
    typically override earlier ones.  ``SourceTracker`` walks the loader list
    in *reverse* order (highest precedence first) so that the first loader
    found to contain the requested key is reported as the authoritative source.

    Attributes:
        loaders: An ordered sequence of loader instances.  Each loader must
            expose a ``config`` attribute (the loaded dictionary) and a
            ``source`` attribute (a human-readable string such as a file path).

    Example:
        >>> tracker = SourceTracker(loaders)
        >>> tracker.get_source("server.port")
        'overrides.yaml'
    """

    def __init__(self, loaders):
        """Initialise the tracker with an ordered list of loaders.

        Args:
            loaders: An iterable of loader instances ordered from lowest to
                highest precedence.  Each loader must have a ``config`` dict
                attribute and a ``source`` string attribute.

        Example:
            >>> tracker = SourceTracker([base_loader, override_loader])
        """
        self.loaders = loaders

    def get_source(self, key):
        """Identify which loader source provides the value for a given key.

        The method supports dot-separated nested keys (e.g.
        ``"database.host"``).  It traverses the loader list in reverse order
        so that the highest-precedence source that contains the key is
        returned first.

        Args:
            key: A dot-separated string representing the configuration key to
                look up.  For example, ``"database.host"`` will traverse into
                ``config["database"]["host"]``.

        Returns:
            The ``source`` string of the loader that contains the key, or
            ``None`` if no loader contains the key.

        Example:
            >>> tracker = SourceTracker(loaders)
            >>> tracker.get_source("database.host")
            'database.yaml'
            >>> tracker.get_source("nonexistent.key") is None
            True
        """
        keys = key.split(".")
        for loader in reversed(self.loaders):
            source_config = loader.config
            try:
                for k in keys:
                    source_config = source_config[k]
                return loader.source
            except KeyError:
                continue
        return None  # Key not found
