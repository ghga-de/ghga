"""Tests for numeric type subschema checking.

Originally created on May 30, 2019 by Andrew Habib.
Contains changes by The GHGA Authors.
SPDX-License-Identifier: Apache-2.0
"""

import pytest
from jsonschema.exceptions import SchemaError

from jsonsubschema import is_subschema
from jsonsubschema._utils import float_gcd

# Tests for integer subtype


def test_integer_identity():
    s1 = {"type": "integer"}
    s2 = s1
    assert is_subschema(s1, s2)


def test_integer_min_min():
    s1 = {"type": "integer", "minimum": 5}
    s2 = {"type": "integer", "minimum": 1}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_integer_max_max():
    s1 = {"type": "integer", "maximum": 10}
    s2 = {"type": "integer", "maximum": 5}
    assert not is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_integer_max_min():
    s1 = {"type": "integer", "maximum": 10}
    s2 = {"type": "integer", "minimum": 5}
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_integer_min_max():
    s1 = {"type": "integer", "minimum": 10}
    s2 = {"type": "integer", "maximum": 20}
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_integer_min_max_min_max1():
    s1 = {"type": "integer", "minimum": 5, "maximum": 10}
    s2 = {"type": "integer", "minimum": 1, "maximum": 20}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_integer_min_max_min_max2():
    s1 = {"type": "integer", "minimum": 5, "maximum": 20}
    s2 = {"type": "integer", "minimum": 10, "maximum": 20}
    assert not is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_integer_min_max_min_max3():
    s1 = {"type": "integer", "minimum": 5, "maximum": 20}
    s2 = {"type": "integer", "minimum": 40, "maximum": 100}
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_integer_xmin_max_min_max():
    s1 = {"type": "integer", "minimum": 5, "exclusiveMinimum": True, "maximum": 20}
    s2 = {"type": "integer", "minimum": 5, "maximum": 20}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_integer_xmin_max_min_xmax():
    s1 = {"type": "integer", "minimum": 5, "exclusiveMinimum": True, "maximum": 20}
    s2 = {"type": "integer", "minimum": 5, "maximum": 20, "exclusiveMaximum": True}
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_integer_xmin_xmax_min_max():
    s1 = {
        "type": "integer",
        "minimum": 5,
        "exclusiveMinimum": True,
        "maximum": 20,
        "exclusiveMaximum": True,
    }
    s2 = {"type": "integer", "minimum": 5, "maximum": 20}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_integer_min_max_xmin_xmax1():
    s1 = {
        "type": "integer",
        "minimum": 5,
        "exclusiveMinimum": True,
        "maximum": 20,
        "exclusiveMaximum": True,
    }
    s2 = {"type": "integer", "minimum": 6, "maximum": 19}
    assert is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_integer_min_max_xmin_xmax2():
    s1 = {
        "type": "integer",
        "minimum": 5,
        "exclusiveMinimum": True,
        "maximum": 20,
        "exclusiveMaximum": True,
    }
    s2 = {"type": "integer", "minimum": 6, "maximum": 20}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_integer_xmin_xmax_xmin_xmax():
    s1 = {
        "type": "integer",
        "minimum": 5,
        "exclusiveMinimum": False,
        "maximum": 20,
        "exclusiveMaximum": True,
    }
    s2 = {
        "type": "integer",
        "minimum": 5,
        "exclusiveMinimum": True,
        "maximum": 20,
        "exclusiveMaximum": True,
    }
    assert not is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_integer_mul_of1():
    s1 = {"type": "integer", "multipleOf": 10}
    s2 = {"type": "integer"}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_integer_mul_of2():
    s1 = {"type": "integer", "multipleOf": 10}
    s2 = {"type": "integer", "multipleOf": 5}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_integer_mul_of3():
    s1 = {"type": "integer", "multipleOf": 10}
    s2 = {"type": "integer", "multipleOf": 98}
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_integer_mul_of_min():
    s1 = {"type": "integer", "multipleOf": 10}
    s2 = {"type": "integer", "minimum": 5}
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_integer_mul_of_min_min():
    s1 = {"type": "integer", "multipleOf": 10, "minimum": 10}
    s2 = {"type": "integer", "minimum": 5}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_integer_mul_of_min_min_max():
    s1 = {"type": "integer", "multipleOf": 10, "minimum": 10}
    s2 = {"type": "integer", "minimum": 5, "maximum": 500}
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_integer_min_max_mul():
    s1 = {"type": "integer", "minimum": 5, "maximum": 10, "multipleOf": 15}
    s2 = {"type": "integer"}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_integer_join1():
    s1 = {
        "anyOf": [
            {"type": "integer", "minimum": 5, "maximum": 10},
            {
                "type": "integer",
            },
        ]
    }
    s2 = {"type": "integer"}
    assert is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_integer_join2():
    s1 = {
        "anyOf": [
            {"type": "integer", "minimum": 5, "maximum": 10},
            {"type": "integer", "minimum": 0},
        ]
    }
    s2 = {"type": "integer"}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_integer_join3():
    s1 = {
        "anyOf": [
            {"type": "integer", "minimum": 5, "maximum": 10},
            {"type": "integer", "minimum": 0, "maximum": 3},
        ]
    }
    s2 = {"type": "integer", "minimum": -1}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_integer_join4():
    s1 = {
        "anyOf": [
            {"type": "integer", "minimum": 5, "maximum": 10},
            {"type": "integer", "minimum": 0, "maximum": 4},
        ]
    }
    s2 = {"type": "integer", "minimum": 1, "maximum": 8}
    assert not is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_integer_join5():
    s1 = {
        "anyOf": [
            {
                "type": "integer",
                "minimum": 5,
                "exclusiveMinimum": True,
                "maximum": 10,
            },
            {"type": "integer", "minimum": 0, "maximum": 4},
        ]
    }
    s2 = {"type": "integer", "minimum": 1, "maximum": 8}
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_integer_join6():
    s1 = {
        "anyOf": [
            {"type": "integer", "minimum": 0, "maximum": 10},
            {"type": "integer", "minimum": 11},
        ]
    }
    s2 = {"type": "integer", "minimum": 0}
    assert is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_integer_join_mulof1():
    s1 = {"anyOf": [{"type": "integer", "multipleOf": 5}, {"type": "integer"}]}
    s2 = {"type": "integer"}
    assert is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_integer_join_mulof2():
    s1 = {
        "anyOf": [
            {"type": "integer", "multipleOf": 5},
            {"type": "integer", "multipleOf": 7},
        ]
    }
    s2 = {"type": "integer"}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_integer_join_mulof3():
    s1 = {
        "anyOf": [
            {"type": "integer", "multipleOf": 5},
            {"type": "integer", "multipleOf": 7},
        ]
    }
    s2 = {"type": "integer", "multipleOf": 35}
    assert not is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_integer_join_mulof4():
    s1 = {
        "anyOf": [
            {"type": "integer", "multipleOf": 5},
            {"type": "integer", "multipleOf": 7},
        ]
    }
    s2 = {"type": "integer", "multipleOf": 5}
    assert not is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_integer_join_mulof5():
    s1 = {
        "anyOf": [
            {"type": "integer", "multipleOf": 3},
            {"type": "integer", "multipleOf": 6},
        ]
    }
    s2 = {"type": "integer", "multipleOf": 3}
    assert is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_integer_join_mulof6():
    s1 = {
        "anyOf": [
            {"type": "integer", "multipleOf": 12},
            {"type": "integer", "multipleOf": 9},
        ]
    }
    s2 = {"type": "integer", "multipleOf": 3}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_integer_join_mulof7():
    s1 = {
        "anyOf": [
            {"type": "integer", "multipleOf": 3, "maximum": 10},
            {"type": "integer", "multipleOf": 5},
        ]
    }
    s2 = {"type": "integer", "multipleOf": 3}
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_integer_join_mulof8():
    s1 = {
        "anyOf": [
            {"type": "integer", "minimum": 5, "maximum": 15, "multipleOf": 5},
            {"type": "integer", "minimum": 5, "maximum": 15, "multipleOf": 3},
        ]
    }
    s2 = {
        "anyOf": [
            {"type": "integer", "minimum": 0, "maximum": 12, "multipleOf": 3},
            {"type": "integer", "minimum": 1, "maximum": 20, "multipleOf": 5},
        ]
    }
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_integer_join_mulof9():
    s1 = {"type": "integer", "minimum": -4, "maximum": 10, "multipleOf": 5}
    s2 = {
        "anyOf": [
            {"type": "integer", "minimum": 0, "maximum": 20, "multipleOf": 10},
            {"type": "integer", "minimum": 1, "maximum": 10, "multipleOf": 5},
        ]
    }
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


# @unittest.skip("Corner case of multipleOf") # check canonicalization/rewrite_enum
def test_integer_join_mulof10():
    s1 = {"enum": [1, 3, 5, 7, 9, 10]}
    s2 = {
        "anyOf": [
            {"type": "integer", "minimum": 0, "maximum": 20, "multipleOf": 10},
            {"type": "integer", "minimum": 1, "maximum": 10, "multipleOf": 5},
            {"enum": [1, 3, 7, 9]},
        ]
    }
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


# Tests for number subtype


def test_number_identity():
    s1 = {"type": "number"}
    s2 = s1
    assert is_subschema(s1, s2)


def test_number_min_min():
    s1 = {"type": "number", "minimum": 5}
    s2 = {"type": "number", "minimum": 1}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_number_max_max():
    s1 = {"type": "number", "maximum": 10}
    s2 = {"type": "number", "maximum": 5}
    assert not is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_number_max_min():
    s1 = {"type": "number", "maximum": 10}
    s2 = {"type": "number", "minimum": 5}
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_number_min_max():
    s1 = {"type": "number", "minimum": 10}
    s2 = {"type": "number", "maximum": 20}
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_number_min_max_min_max1():
    s1 = {"type": "number", "minimum": 5, "maximum": 10}
    s2 = {"type": "number", "minimum": 1, "maximum": 20}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_number_min_max_min_max2():
    s1 = {"type": "number", "minimum": 5, "maximum": 20}
    s2 = {"type": "number", "minimum": 10, "maximum": 20}
    assert not is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_number_min_max_min_max3():
    s1 = {"type": "number", "minimum": 5, "maximum": 20}
    s2 = {"type": "number", "minimum": 40, "maximum": 100}
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_number_xmin_max_min_max():
    s1 = {"type": "number", "minimum": 5, "exclusiveMinimum": True, "maximum": 20}
    s2 = {"type": "number", "minimum": 5, "maximum": 20}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_number_xmin_max_min_xmax():
    s1 = {"type": "number", "minimum": 5, "exclusiveMinimum": True, "maximum": 20}
    s2 = {"type": "number", "minimum": 5, "maximum": 20, "exclusiveMaximum": True}
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_number_xmin_xmax_min_max():
    s1 = {
        "type": "number",
        "minimum": 5,
        "exclusiveMinimum": True,
        "maximum": 20,
        "exclusiveMaximum": True,
    }
    s2 = {"type": "number", "minimum": 5, "maximum": 20}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_number_min_max_xmin_xmax1():
    s1 = {
        "type": "number",
        "minimum": 5,
        "exclusiveMinimum": True,
        "maximum": 20,
        "exclusiveMaximum": True,
    }
    s2 = {"type": "number", "minimum": 6, "maximum": 19}
    assert not is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_number_min_max_xmin_xmax2():
    s1 = {
        "type": "number",
        "minimum": 5,
        "exclusiveMinimum": True,
        "maximum": 20,
        "exclusiveMaximum": True,
    }
    s2 = {"type": "number", "minimum": 6, "maximum": 20}
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_number_xmin_xmax_xmin_xmax():
    s1 = {
        "type": "number",
        "minimum": 5,
        "exclusiveMinimum": False,
        "maximum": 20,
        "exclusiveMaximum": True,
    }
    s2 = {
        "type": "number",
        "minimum": 5,
        "exclusiveMinimum": True,
        "maximum": 20,
        "exclusiveMaximum": True,
    }
    assert not is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_number_mul_of1():
    s1 = {"type": "number", "multipleOf": 10.5}
    s2 = {"type": "number"}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_number_mul_of2():
    s1 = {"type": "number", "multipleOf": 1.5}
    s2 = {"type": "number", "multipleOf": 6}
    assert not is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_number_mul_of3():
    s1 = {"type": "number", "multipleOf": 0.5}
    s2 = {"type": "number", "multipleOf": -0.5}
    with pytest.raises(SchemaError):
        is_subschema(s1, s2)


def test_number_mul_of4():
    s1 = {"type": "number", "multipleOf": 1}
    s2 = {"type": "number"}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_number_mul_of_min():
    s1 = {"type": "number", "multipleOf": 10}
    s2 = {"type": "number", "minimum": 5}
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_number_mul_of_min_min():
    s1 = {"type": "number", "multipleOf": 10, "minimum": 10}
    s2 = {"type": "number", "minimum": 5}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_number_mul_of_min_min_max():
    s1 = {"type": "number", "multipleOf": 10, "minimum": 10}
    s2 = {"type": "number", "minimum": 5, "maximum": 500}
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


# Tests for numeric subtype (integer vs. number)


def test_int_num():
    s1 = {"type": "integer"}
    s2 = {"type": "number"}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_min_num_int():
    s1 = {"type": "number", "minimum": 1.5}
    s2 = {"type": "integer", "minimum": 1}
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_mul_of_num_min_int():
    s1 = {"type": "number", "multipleOf": 10}
    s2 = {"type": "integer", "minimum": 5}
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_mul_of_num_int():
    s1 = {"type": "number", "multipleOf": 10}
    s2 = {"type": "integer"}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_mul_of_num_int2():
    s1 = {"type": "number", "multipleOf": 1}
    s2 = {"type": "integer"}
    assert is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_decimal1():
    s1 = {"maximum": 10.0}
    s2 = {"maximum": 10}

    assert is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_not1():

    pass

    # with self.subTest('LHS < RHS'):
    #     self.assertFalse(is_subschema(s1, s1))
    # with self.subTest('RHS > LHS'):
    #     self.assertTrue(is_subschema(s2, s1))


# Tests for composite numeric subtype


def test_invalid_schema():
    s1 = {"type": "integer"}
    s2 = {"type": "number", "allOf": [""]}
    with pytest.raises(SchemaError):
        is_subschema(s1, s2)
    with pytest.raises(SchemaError):
        is_subschema(s2, s1)


def test_int_int_num1():
    s1 = {"type": "integer"}
    s2 = {
        "type": "number",
        "allOf": [{"type": "integer"}, {"type": "number", "minimum": 10}],
    }
    assert not is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_int_int_num2():
    s1 = {"type": "integer", "multipleOf": 5}
    s2 = {
        "type": "number",
        "allOf": [{"type": "integer"}, {"type": "number", "minimum": 10}],
    }
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_int_mul_mul1():
    s1 = {"type": "integer", "multipleOf": 5}
    s2 = {
        "type": "number",
        "multipleOF": 3,
        "allOf": [{"type": "integer"}, {"type": "number", "multipleOf": 3}],
    }
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_int_mul_mul2():
    s1 = {"type": "integer", "multipleOf": 15}
    s2 = {
        "type": "number",
        "multipleOf": 3,
        "allOf": [{"type": "integer"}, {"type": "number", "multipleOf": 5}],
    }
    assert is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_all_all_1():
    s1 = {
        "type": "integer",
        "allOf": [{"multipleOf": 3}, {"minimum": 5}],
    }  # 6, 9, 12, 15, 18, ...
    s2 = {
        "type": "number",
        "multipleOf": 3,
        "allOf": [{"type": "integer"}, {"type": "number", "multipleOf": 5}],
    }  # ..., -30, -15, 15, 30, 45, ..
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_all_all_2():
    s1 = {"type": "integer", "allOf": [{"multipleOf": 3}]}
    s2 = {
        "type": "number",
        "multipleOf": 3,
        "allOf": [{"type": "integer"}, {"type": "number", "multipleOf": 3}],
    }  # ..., -30, -15, 15, 30, 45, ..
    assert is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_all_all_3():
    s1 = {"type": "number", "allOf": [{"multipleOf": 0.3}]}
    s2 = {
        "type": "number",
        "multipleOf": 3,
        "allOf": [{"type": "integer"}, {"type": "number", "multipleOf": 3}],
    }  # ..., -30, -15, 15, 30, 45, ..
    assert not is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_enum1():
    s1 = {"enum": [1, 2, 3]}
    s2 = {"type": "number"}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_enum2():
    s1 = {"enum": [1.0, 2, 3]}
    s2 = {"enum": [1, 2.0]}
    assert not is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_enum3():
    s1 = {"enum": [1, 2, 3]}
    s2 = {"type": "integer"}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_enum4():
    s1 = {"enum": [1, 2.0, 3]}
    s2 = {"type": "integer"}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


# Tests for numeric utilities


def test_float_gcd():
    assert float_gcd(0.6, 0.4) == 0.2
