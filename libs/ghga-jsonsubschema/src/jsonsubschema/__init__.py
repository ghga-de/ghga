"""
Created on August 6, 2019
@author: Andrew Habib
"""

from jsonsubschema import _canonicalization, api, config
from jsonsubschema import exceptions as exceptions

isSubschema = api.is_subschema
meetSchemas = api.meet
joinSchemas = api.join
isEquivalent = api.is_equivalent

canonicalizeSchema = _canonicalization.canonicalize_schema

set_debug = config.set_debug
set_warn_uninhabited = config.set_warn_uninhabited
