"""Tests for null type subschema checking.

Originally created on June 3, 2019 by Andrew Habib.
Contains changes by The GHGA Authors.
SPDX-License-Identifier: Apache-2.0
"""

from jsonsubschema import isSubschema


def test_null1():
    s1 = {"enum": [None]}
    s2 = {"type": "null"}

    assert isSubschema(s1, s2)
    assert isSubschema(s2, s1)


def test_null2():
    s1 = {"type": "null"}
    s2: dict = {}

    assert isSubschema(s1, s2)
    assert not isSubschema(s2, s1)


def test_null3():
    s1 = {"enum": [None]}
    s2 = {"enum": [0]}

    assert not isSubschema(s1, s2)
    assert not isSubschema(s2, s1)
