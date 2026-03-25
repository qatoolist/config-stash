from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from config_stash.exceptions import ConfigFormatError, ConfigLoadError


class Loader(ABC):
    """Abstract base class for configuration loaders.

    All configuration loaders must inherit from this class and implement
    the `load()` method. This provides a consistent interface for loading
    configuration from various sources (files, remote URLs, environment, etc.).

    Attributes:
        source: The source identifier (file path, URL, prefix, etc.)
        config: The loaded configuration dictionary (may be empty if not loaded yet)
    """

    def __init__(self, source: str) -> None:
        """Initialize the loader with a source.

        Args:
            source: The source identifier (file path, URL, prefix, etc.)
        """
        self.source: str = source
        self.config: Dict[str, Any] = {}

    @abstractmethod
    def load(self) -> Optional[Dict[str, Any]]:
        """Load configuration from the source.

        This method must be implemented by subclasses to load configuration
        from their specific source type.

        Returns:
            Dictionary containing the loaded configuration, or None if the
            source doesn't exist or couldn't be loaded (depending on loader behavior).

        Raises:
            ConfigLoadError: If loading fails due to an error (not just missing source)
            ConfigFormatError: If the configuration format is invalid
        """
        raise NotImplementedError("Load method must be implemented by subclasses")

    def _read_file(self, source: str) -> str:
        """Read file contents from a file path.

        Args:
            source: Path to the file to read

        Returns:
            File contents as a string

        Raises:
            ConfigLoadError: If the file cannot be read
        """
        try:
            with open(source, "r", encoding="utf-8") as file:
                return file.read()
        except FileNotFoundError as e:
            raise ConfigLoadError(
                f"Configuration file not found: {source}",
                source=source,
                loader_type=self.__class__.__name__,
                original_error=e,
            ) from e
        except PermissionError as e:
            raise ConfigLoadError(
                f"Permission denied reading configuration file: {source}",
                source=source,
                loader_type=self.__class__.__name__,
                original_error=e,
            ) from e
        except Exception as e:
            raise ConfigLoadError(
                f"Error reading configuration file: {source}",
                source=source,
                loader_type=self.__class__.__name__,
                original_error=e,
            ) from e

    def _handle_error(self, error: Exception) -> None:
        """Handle errors during configuration loading.

        Args:
            error: The exception that occurred during loading

        Raises:
            ConfigFormatError: For format-related errors
            ConfigLoadError: For other loading errors
        """
        # Try to extract format-specific information from the error
        if hasattr(error, "lineno") and hasattr(error, "colno"):
            raise ConfigFormatError(
                f"Configuration format error in {self.source}",
                source=self.source,
                line_number=getattr(error, "lineno", None),
                column_number=getattr(error, "colno", None),
                original_error=error,
            ) from error

        raise ConfigLoadError(
            f"Error loading configuration from {self.source}",
            source=self.source,
            loader_type=self.__class__.__name__,
            original_error=error,
        ) from error
