Advanced Features
=================

This guide covers advanced Config-Stash features.

Configuration Versioning
------------------------

Track configuration changes over time:

.. code-block:: python

   version_manager = config.enable_versioning()
   version = config.save_version(metadata={"author": "user@example.com"})
   config.rollback_to_version(version.version_id)

Drift Detection
---------------

Detect configuration drift:

.. code-block:: python

   intended = Config(loaders=[YamlLoader("intended.yaml")])
   actual = Config(loaders=[YamlLoader("actual.yaml")])
   drift = actual.detect_drift(intended)

Observability
-------------

Track configuration usage:

.. code-block:: python

   observer = config.enable_observability()
   metrics = config.get_metrics()

Async Support
-------------

Use Config-Stash in async applications:

.. code-block:: python

   from config_stash.async_config import AsyncConfig, AsyncYamlLoader

   async def main():
       config = await AsyncConfig.create(loaders=[AsyncYamlLoader("config.yaml")])
       value = await config.get_async("database.host")
