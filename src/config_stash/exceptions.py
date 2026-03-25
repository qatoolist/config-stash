"""Exception hierarchy for Config-Stash.

This module defines a comprehensive exception hierarchy for better error
handling and debugging throughout the Config-Stash library.
"""

from typing import Any, Dict, Optional


class ConfigStashError(Exception):
    """Base exception for all Config-Stash errors.

    All Config-Stash specific exceptions inherit from this class,
    making it easy to catch any Config-Stash related error.
    """

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error message
            context: Optional context dictionary with additional error information
                    (e.g., file path, line number, key, value)
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}

    def __str__(self) -> str:
        """Return formatted error message with context if available."""
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} ({context_str})"
        return self.message


class ConfigLoadError(ConfigStashError):
    """Raised when configuration loading fails.

    This exception is raised when a loader cannot successfully load
    a configuration from its source (file, remote URL, etc.).
    """

    def __init__(
        self,
        message: str,
        source: Optional[str] = None,
        loader_type: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """Initialize the configuration load error.

        Args:
            message: Error message
            source: Source file/URL that failed to load
            loader_type: Type of loader that failed
            original_error: Original exception that caused this error
        """
        context: Dict[str, Any] = {}
        if source:
            context["source"] = source
        if loader_type:
            context["loader_type"] = loader_type
        if original_error:
            context["original_error"] = str(original_error)
        super().__init__(message, context)
        self.source = source
        self.loader_type = loader_type
        self.original_error = original_error


class ConfigValidationError(ConfigStashError):
    """Raised when configuration validation fails.

    This exception is raised when configuration values don't match
    the expected schema or validation rules.
    """

    def __init__(
        self,
        message: str,
        key: Optional[str] = None,
        value: Any = None,
        schema_path: Optional[str] = None,
        validation_errors: Optional[list] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """Initialize the configuration validation error.

        Args:
            message: Error message
            key: Configuration key that failed validation
            value: Value that failed validation
            schema_path: Path to schema definition (if applicable)
            validation_errors: List of detailed validation errors
            original_error: Original exception that caused this error
        """
        context: Dict[str, Any] = {}
        if key:
            context["key"] = key
        if value is not None:
            context["value"] = value
        if schema_path:
            context["schema_path"] = schema_path
        if validation_errors:
            context["validation_errors"] = validation_errors
        if original_error:
            context["original_error"] = str(original_error)
        super().__init__(message, context)
        self.key = key
        self.value = value
        self.schema_path = schema_path
        self.validation_errors = validation_errors or []
        self.original_error = original_error


class ConfigMergeConflictError(ConfigStashError):
    """Raised when configuration merge conflicts occur.

    This exception is raised when merging configurations results in
    unresolvable conflicts (e.g., incompatible types, conflicting values).
    """

    def __init__(
        self,
        message: str,
        key: str,
        old_value: Any = None,
        new_value: Any = None,
        old_source: Optional[str] = None,
        new_source: Optional[str] = None,
    ) -> None:
        """Initialize the configuration merge conflict error.

        Args:
            message: Error message
            key: Configuration key that has a conflict
            old_value: Value from the base/old configuration
            new_value: Value from the new configuration
            old_source: Source of the old value
            new_source: Source of the new value
        """
        context: Dict[str, Any] = {"key": key}
        if old_value is not None:
            context["old_value"] = old_value
        if new_value is not None:
            context["new_value"] = new_value
        if old_source:
            context["old_source"] = old_source
        if new_source:
            context["new_source"] = new_source
        super().__init__(message, context)
        self.key = key
        self.old_value = old_value
        self.new_value = new_value
        self.old_source = old_source
        self.new_source = new_source


class ConfigNotFoundError(ConfigStashError):
    """Raised when a configuration key or value is not found.

    This exception is raised when trying to access a configuration
    key that doesn't exist.
    """

    def __init__(self, message: str, key: str, available_keys: Optional[list] = None) -> None:
        """Initialize the configuration not found error.

        Args:
            message: Error message
            key: Configuration key that was not found
            available_keys: List of available keys (for helpful error messages)
        """
        context: Dict[str, Any] = {"key": key}
        if available_keys:
            context["available_keys"] = available_keys
        super().__init__(message, context)
        self.key = key
        self.available_keys = available_keys


class ConfigFormatError(ConfigStashError):
    """Raised when a configuration file format is invalid.

    This exception is raised when parsing configuration files fails
    due to format errors (e.g., invalid YAML, malformed JSON).
    """

    def __init__(
        self,
        message: str,
        source: Optional[str] = None,
        line_number: Optional[int] = None,
        column_number: Optional[int] = None,
        format_type: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """Initialize the configuration format error.

        Args:
            message: Error message
            source: Source file with format error
            line_number: Line number where error occurred
            column_number: Column number where error occurred
            format_type: Format type (yaml, json, toml, etc.)
            original_error: Original exception that caused this error
        """
        context: Dict[str, Any] = {}
        if source:
            context["source"] = source
        if line_number:
            context["line_number"] = line_number
        if column_number:
            context["column_number"] = column_number
        if format_type:
            context["format_type"] = format_type
        if original_error:
            context["original_error"] = str(original_error)
        super().__init__(message, context)
        self.source = source
        self.line_number = line_number
        self.column_number = column_number
        self.format_type = format_type
        self.original_error = original_error


class ConfigAccessError(ConfigStashError):
    """Raised when accessing configuration fails.

    This exception is raised when configuration cannot be accessed
    due to permission issues, network problems, etc.
    """

    def __init__(
        self,
        message: str,
        source: Optional[str] = None,
        operation: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """Initialize the configuration access error.

        Args:
            message: Error message
            source: Source that cannot be accessed
            operation: Operation that failed (read, write, list, etc.)
            original_error: Original exception that caused this error
        """
        context: Dict[str, Any] = {}
        if source:
            context["source"] = source
        if operation:
            context["operation"] = operation
        if original_error:
            context["original_error"] = str(original_error)
        super().__init__(message, context)
        self.source = source
        self.operation = operation
        self.original_error = original_error
