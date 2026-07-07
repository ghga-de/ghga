"""Tests for object type subschema checking.

Originally created on July 25, 2019 by Andrew Habib.
Contains changes by The GHGA Authors.
SPDX-License-Identifier: Apache-2.0
"""

import copy

import pytest

from jsonsubschema import is_subschema
from jsonsubschema.exceptions import UnsupportedDependencies

# Tests for object subtype


def test_identity():
    s1 = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "gender": {"type": "string", "maxLength": 1, "enum": ["F", "M"]},
            "email": {"type": "string", "format": "email"},
        },
    }
    s2: dict = copy.deepcopy(s1)
    s2["properties"]["gender"] = {
        "type": "string",
        "maxLength": 1,
        "enum": ["M", "F"],
    }
    assert is_subschema(s1, s2)


def test_min_property():
    s1 = {"type": "object", "minProperties": 1}
    s2 = {"type": "object"}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_max_property():
    s1 = {"type": "object", "maxProperties": 3}
    s2 = {"type": "object"}

    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_min_max_property1():
    s1 = {"type": "object", "minProperties": 1, "maxProperties": 3}
    s2 = {"type": "object"}

    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_min_max_property2():
    s1 = {"type": "object", "minProperties": 1, "maxProperties": 3}
    s2 = {"type": "object", "maxProperties": 5}

    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_min_max_property3():
    s1 = {"type": "object", "minProperties": 1, "maxProperties": 3}
    s2 = {"type": "object", "minProperties": 5, "maxProperties": 2}

    assert not is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_min_max_property4():
    s1 = {"type": "object", "minProperties": 1, "maxProperties": 10}
    s2 = {"type": "object", "minProperties": 2, "maxProperties": 5}

    assert not is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_required1():
    s1 = {"type": "object", "minProperties": 1}
    s2 = {"type": "object", "required": ["p1"]}
    assert not is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_require2():
    s1 = {"type": "object", "minProperties": 1}
    s2 = {"type": "object", "required": ["p1", "p2"]}
    assert not is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_require3():
    s1 = {"type": "object", "maxProperties": 1}
    s2 = {"type": "object", "required": ["p1", "p2"]}
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_require4():
    s1 = {"type": "object", "required": ["p2", "p1"]}
    s2 = {"type": "object", "required": ["p1", "p2"]}
    assert is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_require5():
    s1 = {"type": "object", "required": ["p1"]}
    s2 = {"type": "object", "required": ["p2"]}
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_require6():
    s1 = {"type": "object", "required": ["p1", "p2"]}
    s2 = {"type": "object", "required": ["p2"]}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_require7():
    s1 = {"type": "object", "required": ["p1", "p2"]}
    s2 = {
        "type": "object",
        "required": ["p2"],
        "additionalProperties": {"type": "boolean"},
    }
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_simple_obj1():
    s1 = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "gender": {"type": "string", "maxLength": 1, "enum": ["F", "M"]},
            "email": {"type": "string", "format": "email"},
        },
    }
    s2: dict = copy.deepcopy(s1)
    del s2["properties"]["email"]
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_simple_obj2():
    s1 = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "gender": {"type": "string", "maxLength": 1, "enum": ["F", "M"]},
            "email": {"type": "string", "format": "email"},
        },
    }
    s2 = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "gender": {"type": "string", "maxLength": 1, "enum": ["F", "M"]},
            "email": {"type": "string", "format": "email"},
        },
        "patternProperties": {"^b.*b$": {"type": "boolean"}},
    }
    assert not is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_simple_obj3():
    s1 = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "gender": {"type": "string", "maxLength": 1, "enum": ["F", "M"]},
            "email": {"type": "string", "format": "email"},
        },
        "patternProperties": {"b.*b": {"type": "boolean"}},
    }
    s2 = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "gender": {"type": "string", "maxLength": 1, "enum": ["F", "M"]},
            "email": {"type": "string", "format": "email"},
        },
        "patternProperties": {"^ba+b$": {"type": "boolean"}},
    }
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_simple_obj4():
    s1 = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "gender": {"type": "string", "maxLength": 1, "enum": ["F", "M"]},
            "email": {"type": "string", "format": "email"},
        },
        "patternProperties": {"b.*b": {"type": "integer"}},
    }
    s2 = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "gender": {"type": "string", "maxLength": 1, "enum": ["F", "M"]},
            "email": {"type": "string", "format": "email"},
        },
        "patternProperties": {"^ba+b$": {"type": "boolean"}},
    }
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_simple_obj5():
    s1 = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "gender": {"type": "string", "maxLength": 1, "enum": ["F", "M"]},
            "email": {"type": "string", "format": "email"},
        },
        "patternProperties": {"b.*b": {"type": "integer"}},
    }
    s2 = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "gender": {"type": "string", "maxLength": 1, "enum": ["F", "M"]},
            "email": {"type": "string", "format": "email"},
        },
        "patternProperties": {r"^b(\w)+b$": {"type": "integer", "minimum": 10}},
    }
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_tricky1():
    s1 = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "gender": {"type": "string", "maxLength": 1, "enum": ["F", "M"]},
            "email": {"type": "string", "format": "email"},
            "emaik": {"type": "string", "format": "email"},
        },
    }
    s2 = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "gender": {"type": "string", "maxLength": 1, "enum": ["F", "M"]},
        },
        "patternProperties": {"^emai(l|k)$": {"type": "string"}},
        "required": ["name"],
    }
    assert not is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_tricky2():
    s1 = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "gender": {"type": "string", "maxLength": 1, "enum": ["F", "M"]},
            "email": {"type": "string", "format": "email"},
            "emaik": {"type": "string", "format": "email"},
        },
    }
    s2 = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "gender": {"type": "string", "maxLength": 1, "enum": ["F", "M"]},
        },
        "patternProperties": {"^emai(l|k)$": {"type": "string"}},
    }
    assert is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_tricky3():
    s1 = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "gender": {"type": "string", "maxLength": 1, "enum": ["F", "M"]},
            "email": {"type": "string", "format": "email"},
            "emaik": {"type": "string", "format": "email"},
        },
    }
    s2 = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "gender": {"type": "string", "maxLength": 1, "enum": ["F", "M"]},
        },
        "patternProperties": {"emai": {"type": "string"}},
    }
    assert not is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_tricky4():
    s1 = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "gender": {"type": "string", "maxLength": 1, "enum": ["F", "M"]},
            "email": {"type": "string", "format": "email"},
            "emaik": {"type": "string", "format": "email"},
        },
    }
    s2 = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "gender": {"type": "string", "maxLength": 1, "enum": ["F", "M"]},
        },
        "patternProperties": {"emai": {"type": "string", "minLength": 10}},
    }
    assert not is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_tricky5():
    s1 = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "gender": {"type": "string", "maxLength": 1, "enum": ["F", "M"]},
            "email": {"type": "string", "format": "email"},
            "emaik": {"type": "string", "format": "email"},
        },
        "additionalProperties": {"type": "boolean"},
    }
    s2 = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "gender": {"type": "string", "maxLength": 1, "enum": ["F", "M"]},
        },
        "patternProperties": {"emai": {"type": "string", "minLength": 10}},
    }
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_tricky6():
    s1 = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "gender": {"type": "string", "maxLength": 1, "enum": ["F", "M"]},
            "email": {"type": "string", "format": "email"},
            "emaik": {"type": "string", "format": "email"},
        },
        "additionalProperties": {"type": "boolean"},
    }
    s2 = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "gender": {"type": "string", "maxLength": 1, "enum": ["F", "M"]},
        },
        "patternProperties": {"emai": {"type": "string", "minLength": 10}},
        "additionalProperties": {"type": "boolean"},
    }
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_tricky7():
    s1 = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "gender": {"type": "string", "maxLength": 1, "enum": ["F", "M"]},
            "email": {"type": "string", "format": "email"},
            "emaik": {"type": "string", "format": "email"},
        },
        "additionalProperties": {"type": "string"},
    }

    s2 = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "gender": {"type": "string", "maxLength": 1, "enum": ["F", "M"]},
        },
        "patternProperties": {"emai": {"type": "string"}},
    }
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_required_with_real_schema():
    s1 = {
        "additionalProperties": False,
        "properties": {
            "X": {
                "$schema": "http://json-schema.org/draft-04/schema#",
                "items": {
                    "items": {"type": "number"},
                    "maxItems": 4,
                    "minItems": 4,
                    "type": "array",
                },
                "maxItems": 150,
                "minItems": 150,
                "type": "array",
            },
            "y": {
                "$schema": "http://json-schema.org/draft-04/schema#",
                "items": {"type": "integer"},
                "maxItems": 150,
                "minItems": 150,
                "type": "array",
            },
        },
        "required": ["X", "y"],
        "type": "object",
    }

    s2 = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "additionalProperties": False,
        "description": "Input data schema for training.",
        "properties": {
            "X": {
                "description": "Features; the outer array is over samples.",
                "items": {"items": {"type": "number"}, "type": "array"},
                "type": "array",
            },
            "y": {
                "description": "Target class labels; the array is over samples.",
                "items": {"type": "number"},
                "type": "array",
            },
        },
        "required": ["X", "y"],
        "type": "object",
    }

    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_real_object_schema():
    s1 = {
        "additionalProperties": False,
        "properties": {
            "X": {
                "$schema": "http://json-schema.org/draft-04/schema#",
                "items": {
                    "items": [
                        {"description": "sepal length (cm)", "type": "number"},
                        {"description": "sepal width (cm)", "type": "number"},
                        {"description": "petal length (cm)", "type": "number"},
                        {"description": "petal width (cm)", "type": "number"},
                    ],
                    "maxItems": 4,
                    "minItems": 4,
                    "type": "array",
                },
                "maxItems": 120,
                "minItems": 120,
                "type": "array",
            },
            "y": {
                "$schema": "http://json-schema.org/draft-04/schema#",
                "items": {"description": "target", "type": "integer"},
                "maxItems": 120,
                "minItems": 120,
                "type": "array",
            },
        },
        "required": ["X", "y"],
        "type": "object",
    }

    s2 = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "additionalProperties": False,
        "description": "Input data schema for training.",
        "properties": {
            "X": {
                "description": "Features; the outer array is over samples.",
                "items": {"items": {"type": "number"}, "type": "array"},
                "type": "array",
            },
            "y": {
                "description": "Target class labels; the array is over samples.",
                "items": {"type": "number"},
                "type": "array",
            },
        },
        "required": ["X", "y"],
        "type": "object",
    }

    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_property_top1():
    s1 = {"type": "object", "properties": {"name": {}, "age": {"type": "integer"}}}
    s2 = {"type": "object", "properties": {"age": {"type": "integer"}}}

    assert is_subschema(s1, s2)

    assert is_subschema(s2, s1)


def test_property_top2():
    s1 = {
        "type": "object",
        "properties": {
            "name": {
                "type": [
                    "number",
                    "integer",
                    "string",
                    "boolean",
                    "object",
                    "array",
                    "null",
                ]
            },
            "age": {"type": "integer"},
        },
    }
    s2 = {"type": "object", "properties": {"age": {"type": "integer"}, "name": {}}}

    assert is_subschema(s1, s2)

    assert is_subschema(s2, s1)


# Tests for dependency keyword


def test_dependencies_unsupported():
    # schema dependencies as well as property dependencies are unsupported
    # and fail loudly, on whichever side of the check they appear
    for dependencies in ({"foo": {"type": "string"}}, {"foo": ["bar"]}):
        s1 = {"type": "object", "dependencies": dependencies}
        s2 = {"type": "object"}

        with pytest.raises(UnsupportedDependencies):
            is_subschema(s1, s2)
        with pytest.raises(UnsupportedDependencies):
            is_subschema(s2, s1)


def test_empty_dependencies_ignored():
    # an empty "dependencies" does not constrain anything
    s1 = {"type": "object", "dependencies": {}}
    s2 = {"type": "object"}

    assert is_subschema(s1, s2)
    assert is_subschema(s2, s1)
