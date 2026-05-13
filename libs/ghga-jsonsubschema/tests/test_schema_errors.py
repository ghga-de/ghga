"""Tests for invalid schema error handling.

Originally created on April 24, 2020 by Andrew Habib.
Contains changes by The GHGA Authors.
SPDX-License-Identifier: Apache-2.0
"""

import unittest

from jsonschema import SchemaError

from jsonsubschema import isSubschema


class TestUnknownTypes(unittest.TestCase):
    def test_single_type(self):
        s1 = {"type": "foo"}
        s2: dict = {}

        with self.subTest():
            self.assertRaises(SchemaError, isSubschema, s1, s2)

    def test_list_of_types(self):
        s1 = {"type": ["foo", "string"]}
        s2: dict = {}

        with self.subTest():
            self.assertRaises(SchemaError, isSubschema, s1, s2)
