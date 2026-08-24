"""Tests for invalid schema error handling.

Originally created on April 24, 2020 by Andrew Habib.
Contains changes by The GHGA Authors.
SPDX-License-Identifier: Apache-2.0
"""

import pytest
from jsonschema import SchemaError

from jsonsubschema import is_subschema

# Tests for unknown types


def test_single_type():
    s1 = {"type": "foo"}
    s2: dict = {}

    with pytest.raises(SchemaError):
        is_subschema(s1, s2)


def test_list_of_types():
    s1 = {"type": ["foo", "string"]}
    s2: dict = {}

    with pytest.raises(SchemaError):
        is_subschema(s1, s2)
