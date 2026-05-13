"""Tests for JSON Schema $ref resolution in subschema checking.

Originally created on October 25, 2019 by Andrew Habib.
Contains changes by The GHGA Authors.
SPDX-License-Identifier: Apache-2.0
"""

import pytest

from jsonsubschema import isSubschema
from jsonsubschema.exceptions import UnsupportedRecursiveRef

# Tests for simple $refs


def test_simple_ref_1():
    s1 = {
        "definitions": {"bom": {"type": "string"}, "tak": {"type": "integer"}},
        "type": "object",
        "properties": {"foo": {"$ref": "#/definitions/bom", "type": "integer"}},
    }
    s2 = {"type": "object", "properties": {"foo": {"type": "string"}}}

    assert isSubschema(s1, s2)
    assert isSubschema(s2, s1)


def test_simple_ref_2():
    s1 = {
        "definitions": {"bom": {"type": "string"}, "tak": {"type": "integer"}},
        "type": "object",
        "properties": {"foo": {"$ref": "#/definitions/bom", "type": "integer"}},
    }
    s2 = {
        "type": "object",
        "properties": {"foo": {"type": "string", "pattern": "a"}},
    }

    assert not isSubschema(s1, s2)
    assert isSubschema(s2, s1)


# Tests for $refs


def test_refs_1():
    s1 = {
        "type": "array",
        "items": {"$ref": "#/definitions/positiveInteger"},
        "definitions": {
            "positiveInteger": {
                "type": "integer",
                "minimum": 0,
                "exclusiveMinimum": True,
            }
        },
    }
    s2 = {
        "type": "array",
        "items": {"$ref": "#/definitions/positiveInteger"},
        "definitions": {
            "positiveInteger": {
                "type": "integer",
                "minimum": -1,
                "exclusiveMinimum": True,
            }
        },
    }
    assert isSubschema(s1, s2)
    assert not isSubschema(s2, s1)

    s3 = {"type": "array", "items": {"type": "integer"}}
    assert isSubschema(s1, s3)
    assert isSubschema(s2, s3)

    s4 = {"type": "array", "items": {"type": "string"}}
    assert not isSubschema(s1, s4)
    assert not isSubschema(s2, s4)

    s4 = {"type": "string"}
    assert not isSubschema(s1, s4)
    assert not isSubschema(s2, s4)


@pytest.mark.skip(
    reason="Recursive schema; fails due to jsonschema failure case, not us"
)
def test_refs_2():
    s1 = {
        "definitions": {
            "S": {
                "anyOf": [
                    {"enum": [None]},
                    {
                        "allOf": [
                            {
                                "items": [
                                    {"$ref": "#/definitions/S"},
                                    {"$ref": "#/definitions/S"},
                                ],
                                "maxItems": 2,
                                "minItems": 2,
                                "type": "array",
                            },
                            {"not": {"type": "array", "uniqueItems": True}},
                        ]
                    },
                ]
            }
        },
        "$ref": "#/definitions/S",
    }

    s2 = {"enum": [None]}

    with pytest.raises(UnsupportedRecursiveRef) as exc_info:
        isSubschema(s2, s1)
    print(exc_info.value)


def test_refs_3():
    s1 = {
        "definitions": {
            "person": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "children": {
                        "type": "array",
                        "items": {"$ref": "#/definitions/person"},
                        "default": [],
                    },
                },
            }
        },
        "type": "object",
        "properties": {"person": {"$ref": "#/definitions/person"}},
    }

    s2 = {"enum": [None]}

    with pytest.raises(UnsupportedRecursiveRef) as exc_info:
        isSubschema(s2, s1)
    print(exc_info.value)
