Config-Stash Documentation
===========================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   overview
   installation
   quickstart
   user_guide/index
   api/index
   examples
   contributing

Overview
--------

Config-Stash is a comprehensive, production-ready configuration management library for Python applications.
It provides a unified interface for loading, merging, validating, and accessing configuration from multiple sources
with enterprise-grade features like secret management, schema validation, observability, versioning, and async support.

Key Features
------------

* **Multiple Configuration Sources** - Files (YAML, JSON, TOML), cloud storage, remote URLs, environment variables
* **Secret Store Integration** - AWS Secrets Manager, HashiCorp Vault, Azure Key Vault, GCP Secret Manager
* **Schema Validation** - Pydantic and JSON Schema validation support
* **Dynamic Reloading** - Hot reload with incremental updates
* **Async/Await Support** - First-class async support for async applications
* **Observability** - Metrics, tracing, and event emission
* **Configuration Versioning** - Track changes and rollback configurations
* **Introspection API** - Query and explore configuration programmatically
* **Type Safety** - Full type hints and IDE autocomplete support

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
