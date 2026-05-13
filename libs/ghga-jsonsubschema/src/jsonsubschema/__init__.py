"""Public interface and exports for the jsonsubschema package.

Originally created on August 6, 2019 by Andrew Habib.
Contains changes by The GHGA Authors.
SPDX-License-Identifier: Apache-2.0
"""

from jsonsubschema import exceptions
from jsonsubschema._canonicalization import canonicalize_schema
from jsonsubschema.api import (
    is_equivalent,
    is_subschema,
    join_schemas,
    meet_schemas,
)
from jsonsubschema.config import set_debug, set_warn_uninhabited

__all__ = [
    "canonicalize_schema",
    "exceptions",
    "is_equivalent",
    "is_subschema",
    "join_schemas",
    "meet_schemas",
    "set_debug",
    "set_warn_uninhabited",
]
