"""Configuration loading, merging, reloading, and hook registration mixin.

Handles loading configs from sources, tracking sources, merging,
incremental reload, file watching, extending, and hook registration.
"""

import logging
import os
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from config_stash.config_merger import ConfigMerger
from config_stash.enhanced_source_tracker import SourceInfo
from config_stash.environment_handler import EnvironmentHandler

logger = logging.getLogger(__name__)


class ConfigLoading:
    """Mixin providing config loading, merging, reloading, and hooks."""

    def _get_changed_loaders(self) -> Optional[List]:
        """Get list of loaders for files that have changed.

        Returns:
            List of loaders for changed files, or None if all should be reloaded
        """
        changed_loaders = []
        watched_files = self.get_watched_files()

        for loader in self.loader_manager.loaders:
            source_file = getattr(loader, "source", None)
            if source_file and source_file in watched_files:
                if self.file_tracker.has_changed(source_file):
                    changed_loaders.append(loader)
                    self.file_tracker.update_tracking(source_file)
            else:
                changed_loaders.append(loader)

        return changed_loaders if changed_loaders else None

    def _load_configs_with_tracking(
        self, changed_loaders: Optional[List] = None
    ) -> List[Tuple[Dict[str, Any], str]]:
        """Load configurations with source tracking.

        Args:
            changed_loaders: Optional list of loaders to reload. If None, reload all.

        Returns:
            List of (configuration, source) tuples
        """
        configs = []
        has_env_structure = False

        loaders_to_process = (
            changed_loaders if changed_loaders else self.loader_manager.loaders
        )

        for loader in loaders_to_process:
            try:
                config = loader.load()
            except Exception as e:
                logger.warning(
                    f"Failed to load configuration from "
                    f"{getattr(loader, 'source', loader.__class__.__name__)}: {e}"
                )
                continue
            if config:
                if self._enable_composition:
                    source_file = getattr(
                        loader, "source", loader.__class__.__name__
                    )
                    try:
                        config = self.config_composer.compose(
                            config, source=source_file
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to process composition in {source_file}: {e}"
                        )

                if self.env and self.env in config:
                    has_env_structure = True

                source_file = getattr(
                    loader, "source", loader.__class__.__name__
                )
                loader_type = loader.__class__.__name__
                configs.append((config, source_file, loader_type, loader))

        if has_env_structure and self.env:
            normalized_configs = []
            for config, source_file, loader_type, loader in configs:
                if self.env not in config and "default" not in config:
                    normalized_config = {self.env: config}
                    normalized_configs.append(
                        (normalized_config, source_file, loader_type, loader)
                    )
                else:
                    normalized_configs.append(
                        (config, source_file, loader_type, loader)
                    )
            configs = normalized_configs

        result = []
        for config, source_file, loader_type, loader in configs:
            self.enhanced_source_tracker.track_loader(loader_type, source_file)

            if source_file and os.path.exists(source_file):
                self.file_tracker.track_file(source_file)

            self._track_config_values(config, source_file, loader_type)
            result.append((config, source_file))

        return result

    def _track_env_config(self) -> None:
        """Track environment-extracted config values for easy lookup."""
        if not self.env_config or not self.env:
            return

        env_prefix = f"{self.env}."
        for key in list(self.enhanced_source_tracker.sources.keys()):
            if key.startswith(env_prefix):
                unprefixed_key = key[len(env_prefix):]
                if unprefixed_key not in self.enhanced_source_tracker.sources:
                    source_info = self.enhanced_source_tracker.sources[key]
                    self.enhanced_source_tracker.sources[unprefixed_key] = (
                        SourceInfo(
                            key=unprefixed_key,
                            value=source_info.value,
                            source_file=source_info.source_file,
                            loader_type=source_info.loader_type,
                            line_number=source_info.line_number,
                            environment=source_info.environment,
                            override_count=source_info.override_count,
                        )
                    )

                if key in self.enhanced_source_tracker.override_history:
                    if (
                        unprefixed_key
                        not in self.enhanced_source_tracker.override_history
                    ):
                        self.enhanced_source_tracker.override_history[
                            unprefixed_key
                        ] = self.enhanced_source_tracker.override_history[key]

    def _track_config_values(
        self,
        config: Dict[str, Any],
        source_file: str,
        loader_type: str,
        prefix: str = "",
    ) -> None:
        """Recursively track configuration values."""
        for key, value in config.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                self.enhanced_source_tracker.track_value(
                    full_key,
                    value,
                    source_file,
                    loader_type,
                    environment=self.env if key == self.env else None,
                )
                self._track_config_values(
                    value, source_file, loader_type, full_key
                )
            else:
                self.enhanced_source_tracker.track_value(
                    full_key,
                    value,
                    source_file,
                    loader_type,
                    environment=(
                        self.env
                        if self.env and prefix.startswith(self.env)
                        else None
                    ),
                )

    def _merge_with_tracking(
        self, configs: List[Tuple[Dict[str, Any], str]]
    ) -> Dict[str, Any]:
        """Merge configurations while tracking overrides."""
        if self._advanced_merger:
            merged: Dict[str, Any] = {}
            for config, source in configs:
                merged = self._advanced_merger.merge(merged, config)
            return merged
        else:
            return ConfigMerger.merge_configs(configs, deep_merge=self.deep_merge)

    def reload(
        self,
        validate: Optional[bool] = None,
        dry_run: bool = False,
        incremental: bool = True,
    ) -> None:
        """Reload configuration from all sources.

        Args:
            validate: Optional flag to validate after reload
            dry_run: If True, don't apply changes
            incremental: If True, only reload changed files
        """
        with self._lock:
            self._reload_internal(validate, dry_run, incremental)

    def _reload_internal(
        self,
        validate: Optional[bool] = None,
        dry_run: bool = False,
        incremental: bool = True,
    ) -> None:
        """Internal reload implementation (called under lock)."""
        self._check_frozen()
        logger.info("Reloading configuration...")
        old_config = self.env_config.copy() if self.env_config else {}

        if incremental:
            changed_loaders = self._get_changed_loaders()
            if not changed_loaders:
                logger.info("No configuration files changed, skipping reload")
                return
            logger.info(f"Reloading {len(changed_loaders)} changed file(s)")
        else:
            changed_loaders = None

        reload_start = time.time()

        old_configs = self.configs
        old_merged_config = self.merged_config

        if incremental and changed_loaders:
            changed_sources = {
                getattr(loader, "source", None) for loader in changed_loaders
            }
            existing_configs = [
                (config, source)
                for config, source in self.configs
                if source not in changed_sources
            ]
            new_configs = self._load_configs_with_tracking(
                changed_loaders=changed_loaders
            )
            self.configs = existing_configs + new_configs
        else:
            self.configs = self._load_configs_with_tracking()

        self.merged_config = self._merge_with_tracking(self.configs)
        new_env_config = EnvironmentHandler(
            self.env, self.merged_config
        ).get_env_config()

        reload_duration = time.time() - reload_start
        if self.observer:
            self.observer.record_reload(reload_duration)
        if self.event_emitter:
            self.event_emitter.emit("reload", new_env_config, reload_duration)

        should_validate = (
            validate if validate is not None else self.validate_on_load
        )
        if should_validate and self._schema:
            temp_env_config = self.env_config
            self.env_config = new_env_config
            try:
                self._validate_config()
            except Exception:
                self.env_config = temp_env_config
                raise

        if dry_run:
            self.configs = old_configs
            self.merged_config = old_merged_config
            if should_validate and self._schema:
                self.env_config = temp_env_config
            logger.info("Dry run completed - changes not applied")
            return

        self.env_config = new_env_config
        self._rebuild_state()

        self._trigger_change_callbacks(old_config, self.env_config)

        if self.observer:
            self.observer.record_change()
        if self.event_emitter:
            self.event_emitter.emit("change", old_config, self.env_config)

    def get_watched_files(self) -> List[str]:
        """Get list of files being watched for changes."""
        files = []
        for loader in self.loader_manager.loaders:
            if hasattr(loader, "source"):
                files.append(loader.source)
        return files

    def stop_watching(self) -> None:
        """Stop watching configuration files for changes."""
        if self.dynamic_reloading:
            self.file_watcher.stop()

    def extend(self, loader: Any) -> None:
        """Extend configuration with an additional loader.

        Args:
            loader: Configuration loader instance to add
        """
        self.config_extender.extend_config(loader)

    def register_key_hook(self, key: str, hook: Callable[[Any], Any]) -> None:
        """Register a hook for a specific configuration key."""
        self.hook_processor.register_key_hook(key, hook)

    def register_value_hook(self, value: Any, hook: Callable[[Any], Any]) -> None:
        """Register a hook for a specific value."""
        self.hook_processor.register_value_hook(value, hook)

    def register_condition_hook(
        self, condition: Callable[[str, Any], bool], hook: Callable[[Any], Any]
    ) -> None:
        """Register a hook that runs when a condition is met."""
        self.hook_processor.register_condition_hook(condition, hook)

    def register_global_hook(self, hook: Callable[[Any], Any]) -> None:
        """Register a hook that runs for all configuration values."""
        self.hook_processor.register_global_hook(hook)

    def _generate_ide_support(self) -> None:
        """Automatically generate IDE type stubs for autocomplete."""
        try:
            from config_stash.ide_support import IDESupport

            if self.ide_stub_path is None:
                ide_dir = ".config_stash"
                if not os.path.exists(ide_dir):
                    os.makedirs(ide_dir)
                stub_path = os.path.join(ide_dir, "stubs.pyi")

                init_path = os.path.join(ide_dir, "__init__.py")
                with open(init_path, "w") as f:
                    f.write("# Auto-generated by Config-Stash for IDE support\n")
                    f.write("from .stubs import ConfigType\n")
                    f.write("__all__ = ['ConfigType']\n")
            else:
                stub_path = self.ide_stub_path
                stub_dir = os.path.dirname(stub_path)
                if stub_dir and not os.path.exists(stub_dir):
                    os.makedirs(stub_dir)

            IDESupport.generate_stub(self, stub_path, silent=True)

            if self.dynamic_reloading:

                @self.on_change
                def _update_ide_stubs(key: str, old_value, new_value):
                    if isinstance(new_value, dict) or old_value is None:
                        IDESupport.generate_stub(self, stub_path, silent=True)

        except Exception as e:
            logger.debug(f"IDE support generation skipped: {e}")
