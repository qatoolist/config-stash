Overview
========

What is Config-Stash?
---------------------

Config-Stash is a modern, feature-rich configuration management library designed for Python applications.
It simplifies the complexity of managing application settings across different environments while providing
enterprise-grade capabilities for validation, security, and observability.

Why Config-Stash?
-----------------

Traditional configuration management in Python often involves:
- Manual loading from multiple sources
- Custom validation logic
- No type safety or IDE support
- Difficult debugging of configuration sources
- No built-in secret management

Config-Stash solves these problems by providing:

* **Unified Interface** - Single API for all configuration sources
* **Type Safety** - Full type hints and validation with Pydantic/JSON Schema
* **Secret Management** - Built-in integration with major secret stores
* **Developer Experience** - IDE autocomplete, source tracking, debugging tools
* **Production Ready** - Observability, versioning, drift detection
* **Async Support** - First-class async/await support

Use Cases
---------

Config-Stash is ideal for:

* **Web Applications** - Manage environment-specific configurations
* **Microservices** - Centralized configuration with multiple sources
* **Cloud Applications** - Integration with AWS, Azure, GCP secret stores
* **Enterprise Applications** - Complex configurations with validation
* **DevOps Tools** - Configuration management for infrastructure code
* **CLI Tools** - Simple yet powerful configuration loading

Key Concepts
------------

**Configuration Sources**
   Load from files, environment variables, cloud storage, or custom loaders.

**Environment-Specific Configs**
   Manage different configurations for development, staging, and production.

**Schema Validation**
   Validate configurations against Pydantic models or JSON Schema.

**Secret Resolution**
   Automatically resolve secrets from external stores using placeholders.

**Dynamic Reloading**
   Automatically reload configurations when files change.

**Configuration Composition**
   Include and merge configurations from multiple files.

**Observability**
   Track configuration access patterns and changes with metrics.

For more details, see the :doc:`user_guide/index` section.
