"""
Created on June 24, 2019
@author: Andrew Habib
"""

import jsonref

from jsonsubschema._canonicalization import (
    canonicalize_schema,
    simplify_schema_and_embed_checkers,
)
from jsonsubschema.exceptions import UnsupportedRecursiveRef


def prepare_operands(s1, s2):
    """Resolve $ref, canonicalize, and embed checker objects into both schemas."""
    # First, we load schemas using jsonref to resolve $ref
    # before starting canonicalization.

    # s1 = jsonref.loads(json.dumps(s1))
    # s2 = jsonref.loads(json.dumps(s2))
    # This is not very efficient, should be done lazily maybe?
    s1 = jsonref.JsonRef.replace_refs(s1)
    s2 = jsonref.JsonRef.replace_refs(s2)

    # Canonicalize and embed checkers for both lhs
    # and rhs schemas  before starting the subtype checking.
    # This also validates input schemas and canonicalized schemas.

    # At the moment, recursive/circual refs are not supported and hence, canonicalization
    # throws a RecursionError.
    try:
        _s1 = simplify_schema_and_embed_checkers(canonicalize_schema(s1))
    except RecursionError:
        # avoid cluttering output by unchaining the recursion error
        raise UnsupportedRecursiveRef(s1, "LHS") from None

    try:
        _s2 = simplify_schema_and_embed_checkers(canonicalize_schema(s2))
    except RecursionError:
        # avoid cluttering output by unchaining the recursion error
        raise UnsupportedRecursiveRef(s2, "RHS") from None

    return _s1, _s2


def is_subschema(s1, s2):
    """Entry point for schema subtype checking."""
    s1, s2 = prepare_operands(s1, s2)
    return s1.is_subtype(s2)


def meet(s1, s2):
    """Entry point for schema meet operation."""
    s1, s2 = prepare_operands(s1, s2)
    return s1.meet(s2)


def join(s1, s2):
    """Entry point for schema meet operation."""
    s1, s2 = prepare_operands(s1, s2)
    return s1.join(s2)


def is_equivalent(s1, s2):
    """Entry point for schema equivalence check operation."""
    return is_subschema(s1, s2) and is_subschema(s2, s1)
