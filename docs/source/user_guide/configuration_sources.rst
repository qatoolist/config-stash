Configuration Sources
=====================

Config-Stash supports loading configuration from multiple sources.

File Loaders
------------

Load from YAML, JSON, TOML, INI, or .env files:

.. code-block:: python

   from config_stash.loaders import YamlLoader, JsonLoader, TomlLoader

   config = Config(loaders=[
       YamlLoader("config.yaml"),
       JsonLoader("config.json"),
       TomlLoader("config.toml"),
   ])

Environment Variables
---------------------

Load from environment variables with prefix:

.. code-block:: python

   from config_stash.loaders import EnvironmentLoader

   config = Config(loaders=[
       EnvironmentLoader("APP", separator="__")
   ])

Cloud Storage
-------------

Load from AWS S3, Azure Blob Storage, or Google Cloud Storage:

.. code-block:: python

   from config_stash.loaders import S3Loader

   config = Config(loaders=[
       S3Loader("s3://my-bucket/config.yaml")
   ])

Remote URLs
-----------

Load from HTTP/HTTPS endpoints:

.. code-block:: python

   from config_stash.loaders import HTTPLoader

   config = Config(loaders=[
       HTTPLoader("https://api.example.com/config.yaml")
   ])

For more details, see the :doc:`../api/loaders` documentation.
