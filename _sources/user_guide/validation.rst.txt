Schema Validation
=================

Config-Stash supports validation with Pydantic models and JSON Schema.

Pydantic Validation
-------------------

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

JSON Schema Validation
----------------------

.. code-block:: python

   schema = {
       "type": "object",
       "properties": {
           "database": {
               "type": "object",
               "properties": {
                   "host": {"type": "string"},
                   "port": {"type": "integer"}
               }
           }
       }
   }

   config = Config(
       loaders=[YamlLoader("config.yaml")],
       schema=schema,
       validate_on_load=True
   )
