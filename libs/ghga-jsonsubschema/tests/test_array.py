"""Tests for array type subschema checking.

Originally created on May 30, 2019 by Andrew Habib.
Contains changes by The GHGA Authors.
SPDX-License-Identifier: Apache-2.0
"""

from jsonsubschema import is_subschema

# Tests for array subtype


def test_identity():
    s1 = {"type": "array", "minItems": 5, "maxItems:": 10}
    s2 = s1
    assert is_subschema(s1, s2)


def test_min_max():
    s1 = {"type": "array", "minItems": 5, "maxItems:": 10}
    s2 = {"type": "array", "minItems": 1, "maxItems:": 20}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_unique():
    s1 = {"type": "array", "uniqueItems": True}
    s2 = {"type": "array", "uniqueItems": False}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_empty_items1():
    s1 = {"type": "array"}
    s2 = {"type": "array", "items": {}}
    assert is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_empty_items2():
    s1 = {"type": "array", "additionalItems": False}
    s2 = {"type": "array", "items": {}}
    assert is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_empty_items3():
    s1 = {"type": "array", "items": [{}, {}], "additionalItems": False}
    s2 = {"type": "array", "items": {}}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_empty_items4():
    s1 = {"type": "array", "items": [{}, {}], "additionalItems": True}
    s2 = {"type": "array", "items": {}}
    assert is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_empty_items5():
    s1 = {"type": "array", "items": [{}, {}], "additionalItems": False}
    s2 = {"type": "array", "items": [{}], "additionalItems": False}
    assert not is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_dict_items_list_items1():
    s1 = {"type": "array", "items": {"type": "string"}}
    s2 = {"type": "array", "items": [{"type": "string"}]}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_dict_items_list_items2():
    s1 = {"type": "array", "items": {"type": "string"}}
    s2 = {"type": "array", "items": [{"type": "string"}, {"type": "string"}]}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_dict_items_list_items3():
    s1 = {"type": "array", "items": [{"type": "string"}]}
    s2 = {"type": "array", "items": [{"type": "string"}, {"type": "number"}]}
    assert not is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_dict_items_list_items4():
    s1 = {"type": "array", "items": [{"type": "string"}], "additionalItems": False}
    s2 = {"type": "array", "items": [{"type": "string"}, {"type": "number"}]}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_dict_items_list_items5():
    s1 = {"type": "array", "items": [{"type": "string"}], "additionalItems": True}
    s2 = {"type": "array", "items": [{"type": "string"}, {"type": "number"}]}
    assert not is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_dict_items_list_items6():
    s1 = {"type": "array", "items": [{"type": "string"}], "additionalItems": {}}
    s2 = {"type": "array", "items": [{"type": "string"}, {"type": "number"}]}
    assert not is_subschema(s1, s2)
    assert is_subschema(s2, s1)


# Tests for nested array


def test_1():
    s1 = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "array",
        "minItems": 150,
        "maxItems": 150,
        "items": {
            "type": "array",
            "minItems": 4,
            "maxItems": 4,
            "items": {"type": "number"},
        },
    }

    s2 = {
        "description": "Features; the outer array is over samples.",
        "anyOf": [
            {"type": "array", "items": {"type": "string"}},
            {
                "type": "array",
                "items": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 1,
                    "items": {"type": "string"},
                },
            },
        ],
    }

    assert not is_subschema(s1, s2)
