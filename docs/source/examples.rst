Examples
========

Config-Stash provides comprehensive examples demonstrating all major features.

Basic Examples
--------------

* `basic_usage.py <https://github.com/qatoolist/config-stash/blob/main/examples/basic_usage.py>`_
  - Simple configuration loading
  - Multiple sources
  - Environment variables
  - Environment-specific configs

Introspection API
-----------------

* `introspection_api.py <https://github.com/qatoolist/config-stash/blob/main/examples/introspection_api.py>`_
  - Using keys(), has(), get() methods
  - Schema introspection
  - Configuration explanation

Validation Examples
-------------------

* `validation_example.py <https://github.com/qatoolist/config-stash/blob/main/examples/validation_example.py>`_
  - Pydantic model validation
  - JSON Schema validation
  - Default value application

Async Support
-------------

* `async_example.py <https://github.com/qatoolist/config-stash/blob/main/examples/async_example.py>`_
  - Async configuration loading
  - Parallel loading
  - Async reloading

Advanced Features
-----------------

* `advanced_features.py <https://github.com/qatoolist/config-stash/blob/main/examples/advanced_features.py>`_
  - Versioning
  - Diff and drift detection
  - Observability and metrics
  - Configuration composition

Secret Stores
-------------

* `secret_store_example.py <https://github.com/qatoolist/config-stash/blob/main/examples/secret_store_example.py>`_
  - AWS Secrets Manager
  - HashiCorp Vault
  - Multi-store fallback

Running Examples
----------------

Examples can be run directly:

.. code-block:: bash

   python examples/basic_usage.py
   python examples/introspection_api.py
   python examples/async_example.py

For more examples, see the `examples directory <https://github.com/qatoolist/config-stash/tree/main/examples>`_.
