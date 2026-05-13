"""Public interface and exports for the jsonsubschema package.

Originally created on August 6, 2019 by Andrew Habib.
Contains changes by The GHGA Authors.
SPDX-License-Identifier: Apache-2.0
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
