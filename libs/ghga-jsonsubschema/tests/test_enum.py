"""Tests for enum keyword subschema checking.

Originally created on June 3, 2019 by Andrew Habib.
Contains changes by The GHGA Authors.
SPDX-License-Identifier: Apache-2.0
"""

import pytest

from jsonsubschema import is_subschema
from jsonsubschema.exceptions import UnsupportedEnumCanonicalization

# Tests for enum


def test_enum_simple1():
    s1 = {"enum": [1]}
    s2 = {"enum": [1, 2]}

    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_enum_simple2():
    s1 = {"enum": [True]}
    s2 = {"enum": [1, 2]}

    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_enum_simple3():
    s1 = {"type": "integer", "enum": [1, 2]}
    s2 = {"type": "boolean", "enum": [True]}

    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_enum_simple4():
    s1 = {"enum": ["1", 2]}
    s2 = {"enum": [1, "2"]}

    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_enum_uninhabited1():
    s1 = {"type": "string", "enum": [1, 2]}
    s2 = {"type": "string"}

    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_enum_uninhabited2():
    s1 = {"type": "string", "enum": [0, 1]}
    s2 = {"type": "boolean", "enum": [0]}

    assert is_subschema(s1, s2)
    assert is_subschema(s2, s1)


@pytest.mark.skip(reason="jsonschema.exceptions.SchemaError: [] is too short (enum)")
def test_enum_uninhabited3():
    s1: dict = {"enum": []}
    s2 = {"type": "boolean"}

    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


@pytest.mark.skip(reason="jsonschema.exceptions.SchemaError: [] is too short (enum)")
def test_enum_uninhabited4():
    s1: dict = {"enum": []}
    s2: dict = {"not": {}}

    assert is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_enum_regex_string():
    s1 = {"enum": ["^*"]}
    s2 = {"enum": ["^^"]}

    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


# Tests for enum/const not supported for arrays and objects


def test_array():
    s1: dict = {"enum": [[]]}
    s2 = {"type": "array"}

    with pytest.raises(UnsupportedEnumCanonicalization):
        is_subschema(s1, s2)

    with pytest.raises(UnsupportedEnumCanonicalization) as exc_info:
        is_subschema(s2, s1)
    print(exc_info.value)


def test_object():
    s1 = {"enum": [{"foo": 1}]}
    s2 = {"type": "object"}

    with pytest.raises(UnsupportedEnumCanonicalization):
        is_subschema(s1, s2)

    with pytest.raises(UnsupportedEnumCanonicalization) as exc_info:
        is_subschema(s2, s1)
    print(exc_info.value)
