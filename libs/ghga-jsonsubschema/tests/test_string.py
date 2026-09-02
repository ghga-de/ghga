"""Tests for string type subschema checking.

Originally created on July 11, 2019 by Andrew Habib.
Contains changes by The GHGA Authors.
SPDX-License-Identifier: Apache-2.0
"""

from jsonsubschema import is_equivalent, is_subschema, set_debug

# Tests for string subtype


def test_min_min():
    s1 = {"type": "string", "minLength": 5}
    s2 = {"type": "integer", "maxLength": 1}
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_empty_pattern():
    s1 = {"type": "string", "pattern": ""}
    s2 = {"type": "string"}
    assert is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_regx_range1():
    s1 = {"type": "string", "maxLength": 5, "pattern": "(ab)*"}
    s2 = {"type": "string", "pattern": "(ab){3}"}
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_regx_range2():
    s1 = {"type": "string", "maxLength": 5, "pattern": "^(ab)*$"}
    s2 = {"type": "string", "pattern": "^(ab){0,3}$"}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


# Tests for not-string subtype


def test_str_not_str():
    s1 = {"type": "string"}
    s2 = {"not": s1}
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_str_not_str_with_range():
    s1 = {"type": "string"}
    s2 = {"allOf": [{"type": "string"}, {"not": {"type": "string", "minLength": 2}}]}
    assert not is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_str_not_str_with_range2():
    s1 = {"type": "string", "maxLength": 1}
    s2 = {"allOf": [{"type": "string"}, {"not": {"type": "string", "minLength": 2}}]}
    assert is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_str_not_str_with_range3():
    s1 = {"type": "string", "minLength": 1, "maxLength": 5}
    s2 = {"allOf": [{"type": "string"}, {"not": {"type": "string", "minLength": 2}}]}
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_str_not_str_with_range4():
    s1 = {"type": "string", "minLength": 1, "maxLength": 5}
    s2 = {"allOf": [{"type": "string"}, {"not": {"type": "string", "minLength": 2}}]}
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_not_str_not_str1():
    s1 = {"not": {"type": "string"}}
    s2 = {"not": {"not": {"not": {"type": "string"}}}}
    assert is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_not_str_not_str2():
    s1 = {"not": {"type": "string"}}
    s2 = {"not": {"not": {"type": "string"}}}
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_all_str_not_str1():
    s1 = {"allOf": [{"type": "string"}, {"not": {"type": "string", "minLength": 2}}]}
    s2 = {"type": "string"}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_all_str_not_str2():
    s1 = {"allOf": [{"type": "string"}, {"not": {"type": "string", "minLength": 2}}]}
    s2 = {"type": "string", "maxLength": 1}
    assert is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_all_str_not_str3():
    s1 = {
        "allOf": [
            {"type": "string"},
            {"not": {"type": "string", "minLength": 2, "pattern": "ab"}},
        ]
    }
    s2 = {"type": "string", "maxLength": 1}
    assert not is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_not_str_and_join_string():
    s1 = {
        "allOf": [
            {"type": "string"},
            {"not": {"type": "string", "minLength": 5, "pattern": "a"}},
        ]
    }
    s2 = {
        "anyOf": [
            {"type": "string", "maxLength": 4},
            {"type": "string", "pattern": "[^a]"},
        ]
    }
    set_debug(True)
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)
    set_debug(False)


def test_equiv_multiple_case():
    s1 = {"type": ["string", "null"], "minLength": 1}
    s2 = {"anyOf": [{"type": "string", "minLength": 1}, {"type": "null"}]}
    s3 = {"anyOf": [{"type": "string", "pattern": ".+"}, {"enum": [None]}]}
    s4 = {"type": ["string", "null"], "pattern": ".{1,}"}
    s5 = {"type": ["string", "null"], "not": {"enum": [""]}}

    assert is_equivalent(s1, s2)
    assert is_equivalent(s1, s3)
    assert is_equivalent(s1, s4)
    assert is_equivalent(s1, s5)
    assert is_equivalent(s2, s3)
    assert is_equivalent(s2, s4)
    assert is_equivalent(s2, s5)
    assert is_equivalent(s3, s4)
    assert is_equivalent(s3, s5)
    assert is_equivalent(s4, s5)

    s6 = {"type": ["string", "null"], "pattern": ".{2,}"}
    s7 = {"type": ["string", "null"], "minLength": 2}

    assert is_equivalent(s6, s7)
    assert is_subschema(s6, s1)
    assert not is_subschema(s1, s7)


# Tests for string with enum


def test_enum1():
    s1 = {"type": "string", "enum": ["a"]}
    s2 = {"enum": ["a"]}
    assert is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_enum2():
    s1 = {"type": "string", "enum": ["a"]}
    s2 = {"enum": ["a", "b"]}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_enum3():
    s1 = {"type": "string", "enum": ["a", ""]}
    s2 = {"enum": ["a", "b"]}
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_enum4():
    s1 = {"anyOf": [{"enum": ["a", "b", "c"]}, {"type": "string"}]}
    s2 = {"type": "string"}
    assert is_equivalent(s1, s2)


def test_not_enum1():
    s1 = {"type": "string", "not": {"enum": ["a"]}}
    s2 = {"type": "string"}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_not_enum2():
    s1 = {"type": "string", "not": {"enum": ["a", "b"]}}
    s2 = {"type": "string", "enum": ["a", "b"]}
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)
