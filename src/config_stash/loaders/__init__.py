"""Configuration loaders for Config-Stash.

This module provides loader classes for loading configuration from various
sources including files (YAML, JSON, TOML, INI), environment variables,
and remote sources (HTTP, cloud storage, Git).

Available Loaders
-----------------

File Loaders:
    - YamlLoader: Load from YAML files (.yaml, .yml)
    - JsonLoader: Load from JSON files (.json)
    - TomlLoader: Load from TOML files (.toml)
    - IniLoader: Load from INI files (.ini, .cfg)

Environment Loaders:
    - EnvironmentLoader: Load from system environment variables

Remote Loaders:
    - HTTPLoader: Load from HTTP/HTTPS URLs
    - S3Loader: Load from AWS S3
    - SSMLoader: Load from AWS SSM Parameter Store
    - AzureBlobLoader: Load from Azure Blob Storage
    - GCPStorageLoader: Load from Google Cloud Storage
    - IBMCloudObjectStorageLoader: Load from IBM Cloud Object Storage
    - GitLoader: Load from Git repositories

Example:
    >>> from config_stash.loaders import YamlLoader, EnvironmentLoader
    >>> from config_stash import Config
    >>>
    >>> config = Config(loaders=[
    ...     YamlLoader("config.yaml"),
    ...     EnvironmentLoader("APP")
    ... ])
"""

from config_stash.loaders.env_file_loader import EnvFileLoader
from config_stash.loaders.environment_loader import EnvironmentLoader
from config_stash.loaders.ini_loader import IniLoader
from config_stash.loaders.json_loader import JsonLoader
from config_stash.loaders.loader import Loader
from config_stash.loaders.remote_loader import (
    AzureBlobLoader,
    GCPStorageLoader,
    GitLoader,
    HTTPLoader,
    IBMCloudObjectStorageLoader,
    RemoteLoader,
    S3Loader,
)
from config_stash.loaders.ssm_loader import SSMLoader
from config_stash.loaders.toml_loader import TomlLoader
from config_stash.loaders.yaml_loader import YamlLoader

__all__ = [
    "Loader",
    "JsonLoader",
    "YamlLoader",
    "TomlLoader",
    "EnvironmentLoader",
    "EnvFileLoader",
    "IniLoader",
    "RemoteLoader",
    "HTTPLoader",
    "S3Loader",
    "AzureBlobLoader",
    "GCPStorageLoader",
    "IBMCloudObjectStorageLoader",
    "GitLoader",
    "SSMLoader",
]
