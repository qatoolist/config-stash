Quick Start
===========

This guide will help you get started with Config-Stash in minutes.

Basic Usage
-----------

Load configuration from a single file:

.. code-block:: python

   from config_stash import Config
   from config_stash.loaders import YamlLoader

   config = Config(loaders=[YamlLoader("config.yaml")])
   print(config.database.host)
   print(config.database.port)

Multiple Sources
----------------

Load from multiple sources (later sources override earlier ones):

.. code-block:: python

   from config_stash import Config
   from config_stash.loaders import YamlLoader, EnvironmentLoader

   config = Config(
       env="production",
       loaders=[
           YamlLoader("config/base.yaml"),
           YamlLoader("config/production.yaml"),
           EnvironmentLoader("APP"),  # APP_* environment variables
       ]
   )

With Secret Stores
------------------

Use secret stores for secure credential management:

.. code-block:: python

   from config_stash import Config
   from config_stash.secret_stores import AWSSecretsManager, SecretResolver
   from config_stash.loaders import YamlLoader

   secret_store = AWSSecretsManager(region_name='us-east-1')
   config = Config(
       loaders=[YamlLoader("config.yaml")],
       secret_resolver=SecretResolver(secret_store)
   )
   # Secrets in config.yaml like "${secret:db/password}" are automatically resolved

With Schema Validation
----------------------

Validate configurations with Pydantic models:

.. code-block:: python

   from config_stash import Config
   from pydantic import BaseModel

   class DatabaseConfig(BaseModel):
       host: str
       port: int = 5432

   config = Config(
       loaders=[YamlLoader("config.yaml")],
       schema=DatabaseConfig,
       validate_on_load=True
   )

Debug Mode
----------

Enable debug mode to track configuration sources:

.. code-block:: python

   config = Config(debug_mode=True)
   print(config.get_source("database.host"))  # Shows: 'config/base.yaml'

Next Steps
----------

* See the :doc:`user_guide/index` for detailed usage
* Check out the :doc:`api/index` for complete API reference
* Browse :doc:`examples` for more examples
