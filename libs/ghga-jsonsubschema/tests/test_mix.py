"""Tests for mixed-type and combined keyword subschema checking.

Originally created on June 3, 2019 by Andrew Habib.
Contains changes by The GHGA Authors.
SPDX-License-Identifier: Apache-2.0
"""

from jsonsubschema import is_subschema, set_warn_uninhabited

# Tests for mixed types


def test_t_t_1():
    s1 = {"type": "number"}
    s2 = {"type": "array"}
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_t_t_2():
    s1 = {"type": "number"}
    s2 = {"type": ["number"]}
    assert is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_t_t_3():
    s1 = {"type": "integer"}
    s2 = {"type": ["number"]}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_t_t_4():
    s1 = {"type": "integer"}
    s2 = {"type": ["number", "string"]}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_t_t_5():
    s1 = {"type": ["string", "array"]}
    s2 = {"type": ["number", "string"]}
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_str_int():
    s1 = {
        "type": "string",
        "pattern": "a+",
        "allOf": [
            {"type": "string", "pattern": "b+"},
            {"allOf": [{"type": "string", "maxLength": 10}]},
        ],
    }
    s2 = {"type": "integer", "maxLength": 1}
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_str_bool_any():
    s1 = {"type": ["string", "boolean"]}
    s2 = {"anyOf": [{"type": "string"}, {"type": "boolean"}]}
    assert is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_allany_any():
    s1 = {"allOf": [{"type": ["string", "boolean"]}], "type": ["string", "boolean"]}
    s2 = {"anyOf": [{"type": "string"}, {"type": "boolean"}]}
    assert is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_enum1():
    s1 = {"enum": [1, 2, "test", False]}
    s2 = {"type": ["integer", "string"], "minimum": 10, "enum": [1, 2]}
    assert not is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_enum2():
    s1 = {"allOf": [{"enum": [1, 2, 3]}, {"type": "integer"}], "enum": [3, 4, 5]}
    s2 = {"type": "integer", "enum": [1, 2, 3]}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_enum3():
    s1 = {"enum": [3, 4, 5]}
    s2 = {"enum": [1, 2, 3]}
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_enum4():
    s1 = {"enum": [3, 4, 5]}
    s2 = {"enum": [4, 5, 3]}
    assert is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_enum5():
    s1 = {"enum": [3, 4, 5], "allOf": [{"enum": [1, 2]}]}
    s2 = {"enum": [4, 5, 3]}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_enum6():
    s1 = {"enum": [3, 4, 5], "type": "string"}
    s2 = {"enum": [4, 5, 3]}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_top_nottop():
    s1: dict = {}
    s2 = {"type": "string"}
    assert not is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_top_bot():
    s1: dict = {}
    s2 = {"type": "string", "enum": [1, 2, 3]}
    assert not is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_uninhabited1():
    s1 = {"type": "string", "enum": [2]}
    s2 = {"type": "boolean"}
    set_warn_uninhabited(True)
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)
    set_warn_uninhabited(False)


def test_not_number():
    s1 = {
        "description": "checking_status",
        "enum": ["<0", "0<=X<200", ">=200", "no checking"],
    }
    s2 = {"not": {"type": "number"}}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


# Tests for bottom and top


def test_bot1():
    s1: dict = {"not": {}}
    s2 = {"type": "string"}

    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_bot2():
    s1 = {"description": "bottom", "not": {}}
    s2 = {"type": "string"}

    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_top1():
    s1: dict = {}
    s2 = {"type": "string"}

    assert not is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_top2():
    s1: dict = {"description": "top"}
    s2: dict = {}

    assert is_subschema(s1, s2)
    assert is_subschema(s2, s1)
