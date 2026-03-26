Secret Stores
=============

Config-Stash provides comprehensive secret store integration for secure credential management.

See the detailed documentation: `Secret Stores Guide <https://github.com/qatoolist/config-stash/blob/main/docs/SECRET_STORES.md>`_

Quick Example
-------------

.. code-block:: python

   from config_stash.secret_stores import AWSSecretsManager, SecretResolver

   store = AWSSecretsManager(region_name='us-east-1')
   config = Config(
       loaders=[YamlLoader("config.yaml")],
       secret_resolver=SecretResolver(store)
   )
