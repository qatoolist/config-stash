"""Factory module for creating loader instances from declarative config dicts.

This module provides functions to create loader instances from simple
dictionary definitions, enabling declarative configuration of sources.
"""

import importlib
import os
import re
from typing import Any, Dict, List, Union

from config_stash.exceptions import ConfigStashError
from config_stash.loaders import (
    EnvFileLoader,
    EnvironmentLoader,
    IniLoader,
    JsonLoader,
    TomlLoader,
    YamlLoader,
)
from config_stash.loaders.remote_loader import (
    AzureBlobLoader,
    GCPStorageLoader,
    GitLoader,
    HTTPLoader,
    IBMCloudObjectStorageLoader,
    S3Loader,
)
from config_stash.loaders.ssm_loader import SSMLoader

_ENV_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")


def _expand_env_vars(value: Any) -> Any:
    """Recursively expand ``${VAR}`` patterns in strings, dicts, and lists.

    Environment variable references of the form ``${VAR_NAME}`` are replaced
    with the corresponding value from ``os.environ``.  If the variable is not
    set, the reference is left unchanged.

    Args:
        value: The value to expand.  Strings are scanned for ``${…}``
            patterns; dicts and lists are traversed recursively; all other
            types are returned as-is.

    Returns:
        The value with all recognised environment variable references
        expanded.
    """
    if isinstance(value, str):
        return _ENV_VAR_PATTERN.sub(
            lambda m: os.environ.get(m.group(1), m.group(0)), value
        )
    if isinstance(value, dict):
        return {k: _expand_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env_vars(item) for item in value]
    return value


def create_loader_from_config(source_dict: Dict[str, Any]) -> Any:
    """Create a loader instance from a declarative configuration dictionary.

    The dictionary must contain a ``"type"`` key identifying the loader kind.
    All remaining keys are treated as constructor arguments, with string
    values undergoing environment-variable expansion before being passed to
    the loader constructor.

    Supported types:

    - ``yaml``, ``json``, ``toml``, ``ini`` -- file loaders (require ``path``)
    - ``env_file`` -- ``.env`` file loader (``path`` defaults to ``".env"``)
    - ``environment`` -- environment variable loader (``prefix``, ``separator``)
    - ``ssm`` -- AWS SSM Parameter Store loader
    - ``http`` -- HTTP/HTTPS endpoint loader
    - ``s3`` -- AWS S3 loader
    - ``azure_blob`` -- Azure Blob Storage loader
    - ``gcp_storage`` -- Google Cloud Storage loader
    - ``ibm_cos`` -- IBM Cloud Object Storage loader
    - ``git`` -- Git repository loader (GitHub / GitLab)
    - ``custom`` -- dynamically imported loader class

    Args:
        source_dict: Dictionary describing the source.  Must contain a
            ``"type"`` key.

    Returns:
        An instantiated loader object.

    Raises:
        ConfigStashError: If the ``type`` is unknown or required keys are
            missing.
    """
    # Expand env vars in all values
    expanded: Dict[str, Any] = _expand_env_vars(source_dict)
    source_type: str = expanded.pop("type", None)

    if source_type is None:
        raise ConfigStashError("Source configuration must include a 'type' key")

    # --- file loaders ---
    if source_type == "yaml":
        return YamlLoader(expanded["path"])
    if source_type == "json":
        return JsonLoader(expanded["path"])
    if source_type == "toml":
        return TomlLoader(expanded["path"])
    if source_type == "ini":
        return IniLoader(expanded["path"])

    # --- env file ---
    if source_type == "env_file":
        return EnvFileLoader(expanded.get("path", ".env"))

    # --- environment variables ---
    if source_type == "environment":
        return EnvironmentLoader(
            prefix=expanded.get("prefix", ""),
            separator=expanded.get("separator", "__"),
        )

    # --- AWS SSM ---
    if source_type == "ssm":
        return SSMLoader(
            path_prefix=expanded["path_prefix"],
            decrypt=expanded.get("decrypt", True),
            aws_region=expanded.get("aws_region"),
            aws_access_key_id=expanded.get("aws_access_key_id"),
            aws_secret_access_key=expanded.get("aws_secret_access_key"),
        )

    # --- HTTP ---
    if source_type == "http":
        auth = expanded.get("auth")
        if isinstance(auth, (list, tuple)) and len(auth) == 2:
            auth = tuple(auth)
        else:
            auth = None
        return HTTPLoader(
            url=expanded["url"],
            timeout=expanded.get("timeout", 30),
            headers=expanded.get("headers"),
            auth=auth,
        )

    # --- S3 ---
    if source_type == "s3":
        return S3Loader(
            s3_url=expanded["url"],
            aws_access_key=expanded.get("aws_access_key"),
            aws_secret_key=expanded.get("aws_secret_key"),
            region=expanded.get("region", "us-east-1"),
        )

    # --- Azure Blob ---
    if source_type == "azure_blob":
        return AzureBlobLoader(
            container_url=expanded["container"],
            blob_name=expanded["blob"],
            account_name=expanded.get("account_name"),
            account_key=expanded.get("account_key"),
            sas_token=expanded.get("sas_token"),
            connection_string=expanded.get("connection_string"),
        )

    # --- GCP Storage ---
    if source_type == "gcp_storage":
        return GCPStorageLoader(
            bucket_name=expanded["bucket"],
            blob_name=expanded["blob"],
            project_id=expanded.get("project_id"),
            credentials_path=expanded.get("credentials_path"),
        )

    # --- IBM COS ---
    if source_type == "ibm_cos":
        return IBMCloudObjectStorageLoader(
            bucket_name=expanded["bucket"],
            object_key=expanded["key"],
            api_key=expanded.get("api_key"),
            service_instance_id=expanded.get("service_instance_id"),
            endpoint_url=expanded.get("endpoint_url"),
            region=expanded.get("region", "us-south"),
        )

    # --- Git ---
    if source_type == "git":
        return GitLoader(
            repo_url=expanded["repo"],
            file_path=expanded["file_path"],
            branch=expanded.get("branch", "main"),
            token=expanded.get("token"),
        )

    # --- custom (dynamic import) ---
    if source_type == "custom":
        class_path: str = expanded.pop("class")
        args: Dict[str, Any] = expanded.pop("args", {})
        module_path, class_name = class_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        return cls(**args)

    raise ConfigStashError(f"Unknown source type: '{source_type}'")


def create_loaders_from_config(
    sources_list: List[Dict[str, Any]],
) -> List[Any]:
    """Create multiple loader instances from a list of source definitions.

    Each element in *sources_list* is passed to
    :func:`create_loader_from_config`.  Order is preserved so that later
    sources take precedence during merging, matching the usual convention.

    Args:
        sources_list: List of source configuration dictionaries.

    Returns:
        List of instantiated loader objects, in the same order as the input.
    """
    return [create_loader_from_config(src) for src in sources_list]
