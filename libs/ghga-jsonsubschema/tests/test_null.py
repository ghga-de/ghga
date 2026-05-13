"""Tests for null type subschema checking.

Originally created on June 3, 2019 by Andrew Habib.
Contains changes by The GHGA Authors.
SPDX-License-Identifier: Apache-2.0
"""

from jsonsubschema import is_subschema


def test_null1():
    s1 = {"enum": [None]}
    s2 = {"type": "null"}

    assert is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_null2():
    s1 = {"type": "null"}
    s2: dict = {}

    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_null3():
    s1 = {"enum": [None]}
    s2 = {"enum": [0]}

    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)
