"""Debug and source tracking mixin for Config.

Provides methods for inspecting where configuration values came from,
viewing override history, exporting debug reports, and finding conflicts.
All methods delegate to the EnhancedSourceTracker instance on ``self``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from config_stash.enhanced_source_tracker import SourceInfo

if TYPE_CHECKING:
    from config_stash.enhanced_source_tracker import EnhancedSourceTracker


class ConfigDebug:
    """Mixin providing debug and source-tracking capabilities for Config."""

    # Declared by Config.__init__ — available via mixin composition
    enhanced_source_tracker: EnhancedSourceTracker

    def get_source_info(self, key: str) -> Optional[SourceInfo]:
        """Get detailed source information for a configuration key.

        Args:
            key: Configuration key (dot notation)

        Returns:
            SourceInfo object with detailed tracking information, or None if not found
        """
        return self.enhanced_source_tracker.get_source_info(key)

    def get_override_history(self, key: str) -> List[SourceInfo]:
        """Get the history of overrides for a configuration key.

        Args:
            key: Configuration key (dot notation)

        Returns:
            List of SourceInfo objects showing all values that were overridden
        """
        return self.enhanced_source_tracker.get_override_history(key)

    def print_debug_info(self, key: Optional[str] = None) -> None:
        """Print debug information about configuration sources.

        Args:
            key: Optional specific key to debug, or None for all keys
        """
        self.enhanced_source_tracker.print_debug_info(key)

    def export_debug_report(self, output_path: str = "config_debug_report.json") -> None:
        """Export a detailed debug report to a JSON file.

        Args:
            output_path: Path to output JSON file
        """
        self.enhanced_source_tracker.export_debug_report(output_path)

    def find_keys_from_source(self, source_pattern: str) -> List[str]:
        """Find all configuration keys that came from a specific source.

        Args:
            source_pattern: Source file pattern to search for

        Returns:
            List of configuration keys from matching sources
        """
        return self.enhanced_source_tracker.find_keys_from_source(source_pattern)

    def get_source_statistics(self) -> Dict[str, Any]:
        """Get statistics about configuration sources.

        Returns:
            Dictionary with detailed source statistics
        """
        return self.enhanced_source_tracker.get_source_statistics()

    def get_conflicts(self) -> Dict[str, List[SourceInfo]]:
        """Get all configuration keys that have been overridden.

        Returns:
            Dictionary mapping keys to their override history
        """
        return self.enhanced_source_tracker.get_conflicts()
