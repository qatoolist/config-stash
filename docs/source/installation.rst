Installation
============

Requirements
------------

* Python 3.8 or higher
* pip (Python package installer)

Basic Installation
------------------

Install Config-Stash using pip:

.. code-block:: bash

   pip install config-stash

Optional Dependencies
---------------------

Config-Stash supports optional dependencies for extended functionality:

**Schema Validation**
   Install for Pydantic and JSON Schema validation support:

   .. code-block:: bash

      pip install config-stash[validation]

**Cloud Storage Support**
   Install for cloud storage loaders (AWS S3, Azure, GCP):

   .. code-block:: bash

      pip install config-stash[cloud]

**Secret Store Support**
   Install for secret store integration (AWS, Azure, GCP, Vault):

   .. code-block:: bash

      pip install config-stash[secrets]

**All Features**
   Install all optional dependencies:

   .. code-block:: bash

      pip install config-stash[all]

Individual Secret Store Dependencies
------------------------------------

If you only need specific secret store support:

.. code-block:: bash

   # AWS Secrets Manager
   pip install boto3

   # HashiCorp Vault
   pip install hvac

   # Azure Key Vault
   pip install azure-keyvault-secrets azure-identity

   # GCP Secret Manager
   pip install google-cloud-secret-manager

Verifying Installation
----------------------

Verify the installation:

.. code-block:: python

   from config_stash import Config
   print(Config.__doc__)

Or check the version:

.. code-block:: bash

   python -c "import config_stash; print(config_stash.__version__)"

Next Steps
----------

Now that Config-Stash is installed, see the :doc:`quickstart` guide to get started.
