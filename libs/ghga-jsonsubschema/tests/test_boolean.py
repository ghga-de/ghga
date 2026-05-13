"""Tests for boolean type subschema checking.

Originally created on June 3, 2019 by Andrew Habib.
Contains changes by The GHGA Authors.
SPDX-License-Identifier: Apache-2.0
"""

from jsonsubschema import isSubschema

# Tests for singleton booleans


def test_one_of():
    s1 = {"oneOf": [{"type": "string"}]}
    s2 = {"type": "string"}

    assert isSubschema(s1, s2)
    assert isSubschema(s2, s1)


def test_any_of():
    s1 = {"anyOf": [{"type": "string"}]}
    s2 = {"type": "string"}

    assert isSubschema(s1, s2)
    assert isSubschema(s2, s1)


def test_all_of():
    s1 = {"allOf": [{"type": "string"}]}
    s2 = {"type": "string"}

    assert isSubschema(s1, s2)
    assert isSubschema(s2, s1)


def test_all_of_one_of():
    s1 = {"allOf": [{"type": "string"}]}
    s2 = {"oneOf": [{"type": "string"}]}

    assert isSubschema(s1, s2)
    assert isSubschema(s2, s1)


# Tests for oneOf


def test_oneof1():
    # equiv to {'not': {string}}
    s1 = {"oneOf": [{"type": "string"}, {}]}
    s2 = {"type": "string"}

    assert not isSubschema(s1, s2)
    assert not isSubschema(s2, s1)


def test_oneof2():
    # equiv to {'not': {string}}
    s1 = {"oneOf": [{"type": "string"}, {}]}
    s2 = {"not": {"type": "string"}}

    assert isSubschema(s1, s2)
    assert isSubschema(s2, s1)


def test_oneof4():
    s1 = {"oneOf": [{"type": "boolean"}, {"enum": [True]}]}
    s2 = {"enum": [False]}

    assert isSubschema(s1, s2)
    assert isSubschema(s2, s1)


def test_one_of5():
    # accepts 3 only
    s1 = {"oneOf": [{"enum": [1, 2, 3]}, {"enum": [1, 2]}]}
    s2 = {"enum": [3]}

    assert isSubschema(s1, s2)
    assert isSubschema(s2, s1)


def test_one_of6():
    # accepts 3 only
    s1 = {"oneOf": [{"enum": [1, 2, 3]}, {"enum": [1, 2]}]}
    s2 = {"enum": [1, 2]}

    assert not isSubschema(s1, s2)
    assert not isSubschema(s2, s1)


# Tests for allOf


def test_all_of1():
    s1 = {"allOf": [{"type": "string"}, {"type": "string", "pattern": "a"}]}
    s2 = {"type": "string"}

    assert isSubschema(s1, s2)
    assert not isSubschema(s2, s1)


def test_all_of2():
    s1 = {"allOf": [{"minimum": 10}, {"maximum": 20}]}
    s2 = {"minimum": 10, "maximum": 20}

    assert isSubschema(s1, s2)
    assert isSubschema(s2, s1)


# Tests for not (single boolean combinator)


def test_not_all_of1():
    s1 = {"not": {"allOf": [{"type": "string"}, {"type": "string", "pattern": "a"}]}}
    s2 = {"type": "string"}

    assert not isSubschema(s1, s2)
    assert not isSubschema(s2, s1)


def test_not_all_of2():
    s1 = {"not": {"allOf": [{"type": "string"}, {"type": "string", "pattern": "a"}]}}
    s2 = {
        "anyOf": [
            {"type": "integer"},
            {"type": "number"},
            {"type": "boolean"},
            {"type": "array"},
            {"type": "object"},
            {"type": "string"},
            {"type": "null"},
        ]
    }

    assert isSubschema(s1, s2)
    assert not isSubschema(s2, s1)


def test_not_all_of3():
    s1 = {"not": {"allOf": [{"type": "string"}, {"type": "string", "pattern": "a"}]}}
    s2 = {
        "anyOf": [
            {"type": "integer"},
            {"type": "number"},
            {"type": "boolean"},
            {"type": "array"},
            {"type": "object"},
            {"type": "string", "pattern": "^[^a]*$"},
            {"type": "null"},
        ]
    }

    assert isSubschema(s1, s2)
    assert isSubschema(s2, s1)


def test_not_all_of4():
    s1 = {"not": {"allOf": [{"type": "string"}, {"type": "boolean"}]}}
    s2: dict = {}

    assert isSubschema(s1, s2)
    assert isSubschema(s2, s1)


def test_not_any_of1():
    s1 = {"not": {"anyOf": [{"type": "string"}, {"type": "null"}]}}
    s2 = {"type": "string"}

    assert not isSubschema(s1, s2)
    assert not isSubschema(s2, s1)


def test_not_any_of2():
    s1 = {"not": {"anyOf": [{"type": "string"}, {"type": "null"}]}}
    s2 = {
        "anyOf": [
            {"type": "integer"},
            {"type": "number"},
            {"type": "boolean"},
            {"type": "array"},
            {"type": "object"},
            {"type": "string"},
            {"type": "null"},
        ]
    }

    assert isSubschema(s1, s2)
    assert not isSubschema(s2, s1)


def test_not_one_of1():
    s1 = {"not": {"oneOf": [{"type": "string"}, {"type": "null"}]}}
    s2 = {"type": "string"}

    assert not isSubschema(s1, s2)
    assert not isSubschema(s2, s1)


def test_not_one_of2():
    # accepts anything but 3
    s1 = {"not": {"oneOf": [{"enum": [1, 2, 3]}, {"enum": [1, 2]}]}}
    s2 = {"not": {"enum": [3]}}

    assert isSubschema(s1, s2)
    assert isSubschema(s2, s1)


# Tests for not (combined boolean combinators)


def test_not_and_all_of1():
    s1 = {"not": {"type": "string"}, "allOf": [{"type": "integer"}, {"enum": [5]}]}
    s2 = {"enum": [5]}

    assert isSubschema(s1, s2)
    assert isSubschema(s2, s1)


def test_not_and_any_of1():
    s1 = {
        "not": {"type": "string"},
        "anyOf": [{"type": "integer"}, {"type": "boolean"}],
    }
    s2 = {"type": ["integer", "boolean"]}

    assert isSubschema(s1, s2)
    assert isSubschema(s2, s1)


def test_not_and_two_booleans():
    s1 = {
        "not": {"type": "string"},
        "anyOf": [{"type": "integer"}, {"type": "boolean"}],
        "allOf": [{"minimum": 10}],
    }

    s2 = {"type": ["integer", "boolean"]}

    assert isSubschema(s1, s2)
    assert not isSubschema(s2, s1)


def test_not_and_two_nested_booleans():

    pass

    # with self.subTest('LHS < RHS'):
    #     self.assertTrue(isSubschema(s1, s2))
    # with self.subTest('LHS > RHS'):
    #     self.assertTrue(isSubschema(s2, s1))


def test_two_booleans():
    s1 = {
        "anyOf": [{"type": "integer"}, {"type": "boolean"}],
        "allOf": [{"minimum": 10}, {"maximum": 20}],
    }

    s2 = {"type": ["integer", "boolean"], "minimum": 10, "maximum": 20}

    assert isSubschema(s1, s2)
    assert isSubschema(s2, s1)
