"""IDE autocomplete support for Config-Stash."""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class IDESupport:
    """Generate IDE autocomplete support for configurations.

    Inspects a loaded ``Config`` instance and produces ``.pyi`` type-stub
    files that give editors (PyCharm, VS Code / Pylance, mypy) full
    autocomplete and type-checking for your configuration keys.

    Typical workflow:
      1. Load your ``Config`` as usual.
      2. Call ``IDESupport.generate_stub(config)`` once (e.g., in a
         build script or ``conftest.py``).
      3. Import the generated ``ConfigType`` in your application code for
         editor support.

    Example:
        >>> from config_stash import Config
        >>> from config_stash.ide_support import IDESupport
        >>> config = Config()
        >>> IDESupport.generate_stub(config, output_path=".config_stubs.pyi")
    """

    @staticmethod
    def generate_stub(
        config,  # Config instance
        output_path: str = ".config_stubs.pyi",
        module_name: str = "config_stash_types",
        silent: bool = False,
    ) -> None:
        """Generate type stub file for IDE autocomplete.

        Args:
            config: Config instance with loaded configuration
            output_path: Path to output .pyi file
            module_name: Module name for the generated types
            silent: If True, suppress output messages

        Example:
            config = Config()
            IDESupport.generate_stub(config)

            # Then in your code:
            # from .config_stubs import ConfigType
            # typed_config: ConfigType = config  # type: ignore
        """
        # Get the actual configuration data
        if hasattr(config, "to_dict"):
            config_dict = config.to_dict()
        elif hasattr(config, "merged_config"):
            config_dict = config.merged_config
        elif hasattr(config, "env_config"):
            config_dict = config.env_config
        else:
            raise ValueError("Cannot extract configuration from config object")

        # Generate the stub content
        stub_content = IDESupport._generate_stub_content(config_dict, module_name)

        # Write to file
        with open(output_path, "w") as f:
            f.write(stub_content)

        if not silent:
            logger.info(f"IDE support file generated: {output_path}")
            logger.info(f"   Import with: from .{Path(output_path).stem} import ConfigType")

    @staticmethod
    def _generate_stub_content(config_dict: Dict[str, Any], module_name: str) -> str:
        """Generate the content of the stub file."""
        imports = ["from typing import Any, Optional, Dict, List"]
        classes: List[str] = []

        # Track all class names to avoid duplicates
        generated_classes: Set[str] = set()

        def sanitize_key(key: str) -> str:
            """Convert config key to valid Python identifier."""
            # Replace invalid characters
            key = key.replace("-", "_").replace(".", "_").replace(" ", "_")
            # Ensure it doesn't start with a number
            if key and key[0].isdigit():
                key = f"_{key}"
            return key

        def generate_class(name: str, data: Dict[str, Any], indent: int = 0) -> str:
            """Recursively generate class definitions."""
            if not isinstance(data, dict):
                return ""

            spaces = "    " * indent
            lines = []

            if indent == 0:
                lines.append(f"class {name}:")
            else:
                lines.append(f"{spaces}class {name}:")

            # Add class body
            inner_spaces = "    " * (indent + 1)
            has_content = False

            for key, value in data.items():
                safe_key = sanitize_key(key)

                if isinstance(value, dict) and value:
                    # Nested object - create nested class
                    class_name = f"{safe_key.capitalize()}Type"
                    if class_name not in generated_classes:
                        generated_classes.add(class_name)
                        nested = generate_class(class_name, value, indent + 1)
                        if nested:
                            lines.append(nested)
                    lines.append(f"{inner_spaces}{safe_key}: '{class_name}'")
                    has_content = True
                elif isinstance(value, list):
                    if value and isinstance(value[0], dict):
                        # List of objects
                        item_class = f"{safe_key.capitalize()}Item"
                        if item_class not in generated_classes:
                            generated_classes.add(item_class)
                            nested = generate_class(item_class, value[0], indent + 1)
                            if nested:
                                lines.append(nested)
                        lines.append(f"{inner_spaces}{safe_key}: List['{item_class}']")
                    else:
                        # List of primitives
                        item_type = type(value[0]).__name__ if value else "Any"
                        lines.append(f"{inner_spaces}{safe_key}: List[{item_type}]")
                    has_content = True
                else:
                    # Primitive type
                    type_name = type(value).__name__ if value is not None else "Optional[Any]"
                    if type_name == "NoneType":
                        type_name = "Optional[Any]"
                    lines.append(f"{inner_spaces}{safe_key}: {type_name}")
                    has_content = True

            if not has_content:
                lines.append(f"{inner_spaces}pass")

            return "\n".join(lines)

        # Generate main ConfigType class
        main_class = generate_class("ConfigType", config_dict)

        # Build final content
        stub_lines = []
        stub_lines.extend(imports)
        stub_lines.append("")
        stub_lines.append(main_class)
        stub_lines.append("")
        stub_lines.append("# Usage:")
        stub_lines.append("# from config_stash import Config")
        stub_lines.append(f"# from .{Path(module_name).stem} import ConfigType")
        stub_lines.append("# config: ConfigType = Config()  # type: ignore")
        stub_lines.append("# # Now config.database.host will have autocomplete!")

        return "\n".join(stub_lines)

    @staticmethod
    def enable_auto_generation(config, output_path: str = ".config_stubs.pyi") -> None:
        """Automatically regenerate stubs when configuration changes.

        Registers an ``on_change`` callback on the provided ``Config``
        instance so that the ``.pyi`` stub file is regenerated whenever the
        configuration structure changes (keys added or removed).  This
        keeps IDE autocomplete in sync during development with
        ``dynamic_reloading`` enabled.

        Args:
            config: Config instance with dynamic_reloading enabled
            output_path: Path to output .pyi file

        Example:
            >>> config = Config(dynamic_reloading=True)
            >>> IDESupport.enable_auto_generation(config, ".config_stubs.pyi")
            >>> # Stubs are now regenerated automatically on structural changes.
        """
        if not config.dynamic_reloading:
            logger.warning("Config doesn't have dynamic_reloading enabled")

        # Generate initial stub
        IDESupport.generate_stub(config, output_path)

        # Set up auto-regeneration
        @config.on_change
        def regenerate_stub(key: str, old_value: Any, new_value: Any):
            """Regenerate stub when config structure changes."""
            # Only regenerate if structure changed (new keys added/removed)
            if isinstance(new_value, dict) or old_value is None or new_value is None:
                IDESupport.generate_stub(config, output_path)

        logger.info(f"Auto-generation enabled for {output_path}")

    @staticmethod
    def create_typed_wrapper(config) -> Any:
        """Create a typed wrapper object for runtime attribute access.

        Converts the configuration dictionary into a nested object graph
        so you can access values with ``wrapper.database.host`` instead of
        ``config.get("database.host")``.  This is handy during development
        for quick exploration without generating full stub files.

        Args:
            config: Config instance (must expose ``to_dict()``,
                ``merged_config``, or ``env_config``).

        Returns:
            An object whose attributes mirror the configuration structure.

        Example:
            >>> typed = IDESupport.create_typed_wrapper(config)
            >>> print(typed.database.host)
            'localhost'
        """
        # Get the actual configuration data
        if hasattr(config, "to_dict"):
            config_dict = config.to_dict()
        elif hasattr(config, "merged_config"):
            config_dict = config.merged_config
        elif hasattr(config, "env_config"):
            config_dict = config.env_config
        else:
            raise ValueError("Cannot extract configuration from config object")

        class TypedConfigWrapper:
            """Runtime wrapper with type annotations."""

            def __init__(self, config_dict: Dict[str, Any]):
                self._build_from_dict(config_dict)

            def _build_from_dict(self, data: Dict[str, Any], prefix: str = "") -> None:
                """Recursively build attributes from dictionary."""
                for key, value in data.items():
                    if isinstance(value, dict):
                        # Create nested object
                        nested = type(f"{key.capitalize()}Config", (), {})()
                        for k, v in value.items():
                            setattr(nested, k, v)
                        setattr(self, key, nested)
                    else:
                        setattr(self, key, value)

        return TypedConfigWrapper(config_dict)


# Optional: VSCode specific support
class VSCodeSupport:
    """Generate VS Code-specific editor configuration.

    Creates or updates ``.vscode/settings.json`` with Python analysis
    settings (extra paths, type-checking mode, mypy integration) so that
    Config-Stash type stubs are picked up automatically by Pylance and
    mypy within VS Code.

    Example:
        >>> VSCodeSupport.generate_settings()
        >>> # .vscode/settings.json is now configured for type support.
    """

    @staticmethod
    def generate_settings() -> None:
        """Generate .vscode/settings.json for better IDE support."""
        vscode_dir = Path(".vscode")
        vscode_dir.mkdir(exist_ok=True)

        settings = {
            "python.analysis.extraPaths": ["."],
            "python.analysis.autoImportCompletions": True,
            "python.analysis.typeCheckingMode": "basic",
            "python.linting.mypyEnabled": True,
            "python.linting.mypyArgs": ["--ignore-missing-imports", "--follow-imports=silent"],
        }

        import json

        settings_path = vscode_dir / "settings.json"

        # Merge with existing settings if file exists
        if settings_path.exists():
            with open(settings_path, "r") as f:
                existing = json.load(f)
                settings.update(existing)

        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=2)

        logger.info(f"VSCode settings generated: {settings_path}")


# Usage example in docstring
"""
Example usage for IDE autocomplete:

    from config_stash import Config
    from config_stash.ide_support import IDESupport

    # Load your configuration
    config = Config()

    # Generate type stubs for IDE support
    IDESupport.generate_stub(config)

    # Now in your application code:
    from .config_stubs import ConfigType

    config: ConfigType = Config()  # type: ignore on this line only

    # Full autocomplete works now!
    print(config.database.host)  # IDE knows this exists!
    print(config.database.port)  # And the type!

    # Or use the runtime wrapper for both autocomplete and validation:
    typed_config = IDESupport.create_typed_wrapper(config)
    print(typed_config.database.host)  # Works with autocomplete!
"""
