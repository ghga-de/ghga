"""Tests for JSON Schema const keyword subtype checking.

Originally created by Andrew Habib.
Contains changes by The GHGA Authors.
SPDX-License-Identifier: Apache-2.0
"""

import pytest

from jsonsubschema import isSubschema
from jsonsubschema.exceptions import UnsupportedEnumCanonicalization

# Tests for const


def test_const_equal_num() -> None:
    s1 = {"const": 1}
    s2 = {"const": 1}

    assert isSubschema(s1, s2)
    assert isSubschema(s2, s1)


def test_const_equal_str() -> None:
    s1 = {"const": "a"}
    s2 = {"const": "a"}

    assert isSubschema(s1, s2)
    assert isSubschema(s2, s1)


def test_const_vs_enum() -> None:
    s1 = {"const": 1}
    s2 = {"enum": [1, 2]}

    assert isSubschema(s1, s2)
    assert not isSubschema(s2, s1)


def test_const_vs_wrong_enum() -> None:
    s1 = {"const": 1}
    s2 = {"enum": [2, 3]}

    assert not isSubschema(s1, s2)
    assert not isSubschema(s2, s1)


def test_const_vs_type() -> None:
    s1 = {"const": 1}
    s2 = {"type": "integer"}

    assert isSubschema(s1, s2)
    assert not isSubschema(s2, s1)


def test_const_vs_wrong_type() -> None:
    s1 = {"const": 1}
    s2 = {"type": "string"}

    assert not isSubschema(s1, s2)
    assert not isSubschema(s2, s1)


def test_const_type_mix() -> None:
    s1 = {"const": "1"}
    s2 = {"const": 1}

    assert not isSubschema(s1, s2)
    assert not isSubschema(s2, s1)


def test_enum_uninhabited1() -> None:
    s1 = {"type": "string", "const": 1}
    s2 = {"type": "string"}

    assert isSubschema(s1, s2)
    assert not isSubschema(s2, s1)


def test_enum_uninhabited2() -> None:
    s1 = {"type": "string", "const": 1}
    s2 = {"type": "boolean", "const": 1}

    assert isSubschema(s1, s2)
    assert isSubschema(s2, s1)


# Tests for enum/const not supported for arrays and objects


def test_array() -> None:
    s1: dict = {"const": []}
    s2 = {"type": "array"}

    with pytest.raises(UnsupportedEnumCanonicalization):
        isSubschema(s1, s2)

    with pytest.raises(UnsupportedEnumCanonicalization):
        isSubschema(s2, s1)


def test_object() -> None:
    s1: dict = {"const": {}}
    s2 = {"type": "object"}

    with pytest.raises(UnsupportedEnumCanonicalization):
        isSubschema(s1, s2)

    with pytest.raises(UnsupportedEnumCanonicalization):
        isSubschema(s2, s1)
