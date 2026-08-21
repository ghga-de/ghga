"""Public API for JSON Schema subtype checking.

Originally created on June 24, 2019 by Andrew Habib.
Contains changes by The GHGA Authors.
SPDX-License-Identifier: Apache-2.0
"""

import jsonref

from jsonsubschema._canonicalization import (
    canonicalize_schema,
    simplify_schema_and_embed_checkers,
)
from jsonsubschema.exceptions import UnsupportedRecursiveRef

__all__ = [
    "is_equivalent",
    "is_subschema",
    "join_schemas",
    "meet_schemas",
]


def prepare_operands(s1, s2):
    """Resolve $ref, canonicalize, and embed checker objects into both schemas."""
    # First, we load schemas using jsonref to resolve $ref
    # before starting canonicalization.
    s1 = jsonref.JsonRef.replace_refs(s1)
    s2 = jsonref.JsonRef.replace_refs(s2)

    # Canonicalize and embed checkers for both lhs
    # and rhs schemas  before starting the subtype checking.
    # This also validates input schemas and canonicalized schemas.

    def _canonicalize_or_raise(schema, side):
        # At the moment, recursive/circular refs are not supported and hence,
        # canonicalization throws a RecursionError.
        try:
            return simplify_schema_and_embed_checkers(canonicalize_schema(schema))
        except RecursionError:
            # avoid cluttering output by unchaining the recursion error
            raise UnsupportedRecursiveRef(schema, side) from None

    return _canonicalize_or_raise(s1, "LHS"), _canonicalize_or_raise(s2, "RHS")


def is_subschema(s1, s2):
    """Entry point for schema subtype checking."""
    s1, s2 = prepare_operands(s1, s2)
    return s1.is_subtype(s2)


def meet_schemas(s1, s2):
    """Entry point for schema meet operation."""
    s1, s2 = prepare_operands(s1, s2)
    return s1.meet(s2)


def join_schemas(s1, s2):
    """Entry point for schema join operation."""
    s1, s2 = prepare_operands(s1, s2)
    return s1.join(s2)


def is_equivalent(s1, s2):
    """Entry point for schema equivalence check."""
    return is_subschema(s1, s2) and is_subschema(s2, s1)
