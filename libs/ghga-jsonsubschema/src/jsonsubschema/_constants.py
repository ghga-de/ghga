"""JSON Schema type and keyword constants.

Originally created on June 7, 2019 by Andrew Habib.
Contains changes by The GHGA Authors.
SPDX-License-Identifier: Apache-2.0
"""

import operator
from functools import reduce

Jnumeric = {"integer", "number"}

Jtypes = Jnumeric.union(["string", "boolean", "null", "array", "object"])

JallTypes = Jnumeric.union(Jtypes)

JtypesToKeywords = {
    "string": ["minLength", "maxLength", "pattern"],
    "number": [
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "multipleOf",
    ],
    "integer": [
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "multipleOf",
    ],
    "boolean": [],
    "null": [],
    "array": ["minItems", "maxItems", "items", "additionalItems", "uniqueItems"],
    "object": [
        "properties",
        "additionalProperties",
        "required",
        "minProperties",
        "maxProperties",
        "dependencies",
        "patternProperties",
    ],
}

JtypesRestrictionKeywords = reduce(operator.add, JtypesToKeywords.values())

Jconnectors = {"anyOf", "allOf", "oneOf", "not"}

Jcommonkw = Jconnectors.union(["enum", "type", "const"])

JNonValidation = {"$schema", "$id", "definitions", "title", "description", "format"}

# JNonValidation is deliberately not part of Jkeywords:
# including it would conflict with canonicalize_connectors.
Jkeywords = Jcommonkw.union(Jtypes, JtypesRestrictionKeywords, ["$ref"])

JtypesToPyTypes = {
    "integer": int,
    "number": float,
    "string": str,
    "boolean": bool,
    "null": type(None),
    "array": list,
    "object": dict,
}

PyTypesToJtypes = {v: k for k, v in JtypesToPyTypes.items()}
