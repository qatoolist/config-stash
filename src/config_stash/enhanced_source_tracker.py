"""Enhanced source tracking for configuration values with debug support."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class SourceInfo:
    """Information about where a configuration value came from."""

    key: str
    value: Any
    source_file: str
    loader_type: str
    line_number: Optional[int] = None
    override_count: int = 0
    overridden_by: List[str] = field(default_factory=list)
    original_sources: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    environment: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "key": self.key,
            "value": self.value,
            "source_file": self.source_file,
            "loader_type": self.loader_type,
            "line_number": self.line_number,
            "override_count": self.override_count,
            "overridden_by": self.overridden_by,
            "original_sources": self.original_sources,
            "timestamp": self.timestamp.isoformat(),
            "environment": self.environment,
        }

    def __str__(self) -> str:
        """Human-readable string representation."""
        result = f"Key: {self.key}\n"
        result += f"Current Value: {self.value}\n"
        result += f"Source: {self.source_file} (via {self.loader_type})\n"

        if self.line_number:
            result += f"Line Number: {self.line_number}\n"

        if self.environment:
            result += f"Environment: {self.environment}\n"

        if self.override_count > 0:
            result += f"Override Count: {self.override_count}\n"
            result += f"Overridden by: {', '.join(self.overridden_by)}\n"
            if self.original_sources:
                result += f"Original Sources: {', '.join(self.original_sources)}\n"

        return result


class EnhancedSourceTracker:
    """Enhanced source tracking with detailed debugging information."""

    def __init__(self, debug_mode: bool = False):
        """Initialize the enhanced source tracker.

        Args:
            debug_mode: Enable detailed source tracking and debugging
        """
        self.debug_mode = debug_mode
        self.sources: Dict[str, SourceInfo] = {}
        self.override_history: Dict[str, List[SourceInfo]] = {}
        self.loader_order: List[Tuple[str, str]] = []  # (loader_type, source_file)
        self._value_map: Dict[str, Any] = {}

    def track_value(
        self,
        key: str,
        value: Any,
        source_file: str,
        loader_type: str,
        line_number: Optional[int] = None,
        environment: Optional[str] = None,
    ) -> None:
        """Track a configuration value and its source.

        Args:
            key: Configuration key (dot notation)
            value: Configuration value
            source_file: File or source where value came from
            loader_type: Type of loader used (e.g., "YamlLoader", "EnvironmentLoader")
            line_number: Line number in source file (if applicable)
            environment: Environment name (if environment-specific)
        """
        if not self.debug_mode:
            # In non-debug mode, just track basic info
            self.sources[key] = SourceInfo(
                key=key,
                value=value,
                source_file=source_file,
                loader_type=loader_type,
                environment=environment,
            )
            return

        # In debug mode, track full history
        if key in self.sources:
            # Value is being overridden
            old_info = self.sources[key]

            # Track override history
            if key not in self.override_history:
                self.override_history[key] = []
            self.override_history[key].append(old_info)

            # Create new source info with override tracking
            new_info = SourceInfo(
                key=key,
                value=value,
                source_file=source_file,
                loader_type=loader_type,
                line_number=line_number,
                environment=environment,
                override_count=old_info.override_count + 1,
                overridden_by=(
                    [source_file]
                    if source_file not in old_info.overridden_by
                    else old_info.overridden_by
                ),
                original_sources=(
                    old_info.original_sources + [old_info.source_file]
                    if old_info.source_file not in old_info.original_sources
                    else old_info.original_sources
                ),
            )

            self.sources[key] = new_info
        else:
            # First time seeing this key
            self.sources[key] = SourceInfo(
                key=key,
                value=value,
                source_file=source_file,
                loader_type=loader_type,
                line_number=line_number,
                environment=environment,
            )

        # Track value for comparison
        self._value_map[key] = value

    def track_loader(self, loader_type: str, source_file: str) -> None:
        """Track the order of loaders.

        Args:
            loader_type: Type of loader
            source_file: Source file or identifier
        """
        self.loader_order.append((loader_type, source_file))

    def get_source(self, key: str) -> Optional[str]:
        """Get the source file for a configuration key.

        Args:
            key: Configuration key (dot notation)

        Returns:
            Path to source file or None if not found
        """
        if key in self.sources:
            return self.sources[key].source_file

        # Check for parent keys (e.g., "database.host" -> check "database")
        parts = key.split(".")
        for i in range(len(parts) - 1, 0, -1):
            parent_key = ".".join(parts[:i])
            if parent_key in self.sources:
                return self.sources[parent_key].source_file

        return None

    def get_source_info(self, key: str) -> Optional[SourceInfo]:
        """Get detailed source information for a key.

        Args:
            key: Configuration key (dot notation)

        Returns:
            SourceInfo object or None if not found
        """
        return self.sources.get(key)

    def get_override_history(self, key: str) -> List[SourceInfo]:
        """Get the override history for a key.

        Args:
            key: Configuration key (dot notation)

        Returns:
            List of SourceInfo objects showing override history
        """
        return self.override_history.get(key, [])

    def get_all_sources(self) -> Dict[str, SourceInfo]:
        """Get all tracked source information.

        Returns:
            Dictionary mapping keys to SourceInfo objects
        """
        return self.sources.copy()

    def get_loader_order(self) -> List[Tuple[str, str]]:
        """Get the order in which loaders were applied.

        Returns:
            List of (loader_type, source_file) tuples
        """
        return self.loader_order.copy()

    def get_conflicts(self) -> Dict[str, List[SourceInfo]]:
        """Get all keys that have been overridden.

        Returns:
            Dictionary mapping keys to their override history
        """
        return {
            key: history for key, history in self.override_history.items() if history
        }

    def print_debug_info(self, key: Optional[str] = None) -> None:
        """Print debug information for a key or all keys.

        Args:
            key: Specific key to debug, or None for all keys
        """
        if not self.debug_mode:
            print(
                "Debug mode is not enabled. Set debug_mode=True to track detailed source information."
            )
            return

        print("=" * 80)
        print("Configuration Source Debug Information")
        print("=" * 80)

        if key:
            # Debug specific key
            if key in self.sources:
                print(f"\n{self.sources[key]}")

                # Show override history if available
                if key in self.override_history:
                    print("\nOverride History:")
                    print("-" * 40)
                    for i, info in enumerate(self.override_history[key], 1):
                        print(f"\nOverride #{i}:")
                        print(f"  Source: {info.source_file}")
                        print(f"  Value: {info.value}")
                        print(f"  Timestamp: {info.timestamp.isoformat()}")
            else:
                print(f"\nKey '{key}' not found in tracked sources.")

                # Suggest similar keys
                similar = [k for k in self.sources.keys() if key in k or k in key]
                if similar:
                    print("\nSimilar keys found:")
                    for k in similar:
                        print(f"  - {k}")
        else:
            # Show all sources
            print(f"\nTotal tracked keys: {len(self.sources)}")
            print(f"Keys with overrides: {len(self.override_history)}")
            print("\nLoader Order:")
            print("-" * 40)
            for i, (loader_type, source) in enumerate(self.loader_order, 1):
                print(f"  {i}. {loader_type}: {source}")

            if self.override_history:
                print("\nConflicting Keys (overridden values):")
                print("-" * 40)
                for key, history in self.override_history.items():
                    current = self.sources[key]
                    print(f"\n  {key}:")
                    print(f"    Current: {current.value} (from {current.source_file})")
                    print(f"    Overridden {len(history)} time(s)")
                    for info in history[-3:]:  # Show last 3 overrides
                        print(f"      - Was: {info.value} (from {info.source_file})")

    def export_debug_report(
        self, output_path: str = "config_debug_report.json"
    ) -> None:
        """Export a detailed debug report to a JSON file.

        Args:
            output_path: Path to output JSON file
        """
        if not self.debug_mode:
            print(
                "Debug mode is not enabled. Set debug_mode=True to export debug reports."
            )
            return

        report = {
            "timestamp": datetime.now().isoformat(),
            "loader_order": self.loader_order,
            "total_keys": len(self.sources),
            "overridden_keys": len(self.override_history),
            "sources": {key: info.to_dict() for key, info in self.sources.items()},
            "override_history": {
                key: [info.to_dict() for info in history]
                for key, history in self.override_history.items()
            },
        }

        with open(output_path, "w") as f:
            json.dump(report, f, indent=2, default=str)

        print(f"Debug report exported to: {output_path}")

    def find_keys_from_source(self, source_pattern: str) -> List[str]:
        """Find all keys that came from a specific source.

        Args:
            source_pattern: Source file pattern to search for

        Returns:
            List of keys from matching sources
        """
        matching_keys = []
        for key, info in self.sources.items():
            if source_pattern in info.source_file:
                matching_keys.append(key)
        return matching_keys

    def get_source_statistics(self) -> Dict[str, Any]:
        """Get statistics about configuration sources.

        Returns:
            Dictionary with source statistics
        """
        sources_by_loader: Dict[str, int] = {}
        keys_by_source: Dict[str, int] = {}

        stats: Dict[str, Any] = {
            "total_keys": len(self.sources),
            "total_overrides": sum(
                info.override_count for info in self.sources.values()
            ),
            "unique_sources": len({info.source_file for info in self.sources.values()}),
            "keys_with_overrides": len(self.override_history),
            "sources_by_loader": sources_by_loader,
            "keys_by_source": keys_by_source,
        }

        # Count by loader type
        for info in self.sources.values():
            loader = info.loader_type
            if loader not in sources_by_loader:
                sources_by_loader[loader] = 0
            sources_by_loader[loader] += 1

            # Count by source file
            source = info.source_file
            if source not in keys_by_source:
                keys_by_source[source] = 0
            keys_by_source[source] += 1

        return stats
