"""Tests for numeric type subschema checking.

Originally created on May 30, 2019 by Andrew Habib.
Contains changes by The GHGA Authors.
SPDX-License-Identifier: Apache-2.0
"""

import pytest
from jsonschema.exceptions import SchemaError

from jsonsubschema import is_equivalent, is_subschema, meet_schemas
from jsonsubschema._utils import float_gcd
from jsonsubschema.exceptions import UnsupportedNegatedNumeric

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


def test_int_mul_of_fraction():
    # every integer is a multiple of 0.5, but not of 0.4 (e.g. 1)
    s1 = {"type": "integer"}
    s2 = {"type": "number", "multipleOf": 0.5}
    s3 = {"type": "number", "multipleOf": 0.4}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)
    assert not is_subschema(s1, s3)


def test_single_value_mul_of():
    # subtype checks of single-value schemas are decided by validation
    s1 = {"type": "integer", "minimum": 10, "maximum": 10}
    assert is_subschema(s1, {"type": "number", "multipleOf": 2})
    assert not is_subschema(s1, {"type": "number", "multipleOf": 3})
    assert is_subschema(
        {"type": "number", "minimum": 10.5, "maximum": 10.5},
        {"type": "number", "multipleOf": 0.5},
    )


def test_mul_of_without_multiple_in_range_uninhabited():
    # there is no multiple of 10 in [12, 18], so s1 is uninhabited
    s1 = {"type": "number", "multipleOf": 10, "minimum": 12, "maximum": 18}
    assert is_subschema(s1, {"type": "string"})
    # but 0 and -10 are multiples of 10 below 5
    s2 = {"type": "number", "multipleOf": 10, "maximum": 5}
    assert not is_subschema(s2, {"type": "string"})


def test_decimal1():
    s1 = {"maximum": 10.0}
    s2 = {"maximum": 10}

    assert is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_not1():
    # s1 admits everything but the integers 10..20 (e.g. "x" and 10.5),
    # while s2 only admits numbers below 10 or above 20
    s1 = {"not": {"type": "integer", "minimum": 10, "maximum": 20}}
    s2 = {"not": {"minimum": 10, "maximum": 20}}

    assert not is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_not_number_minimum():
    # the complement of x >= 5 over numbers is x < 5
    s1 = {"type": "number", "maximum": 5, "exclusiveMaximum": True}
    s2 = {"type": "number", "maximum": 5}
    neg = {"not": {"type": "number", "minimum": 5}}
    assert is_subschema(s1, neg)
    assert not is_subschema(s2, neg)


def test_not_number_exclusive_minimum():
    # the complement of x > 5 over numbers is x <= 5
    s1 = {"type": "number", "maximum": 5}
    s2 = {"type": "number", "maximum": 6}
    neg = {"not": {"type": "number", "minimum": 5, "exclusiveMinimum": True}}
    assert is_subschema(s1, neg)
    assert not is_subschema(s2, neg)


def test_not_number_maximum():
    # the complement of x <= 5 over numbers is x > 5
    s1 = {"type": "number", "minimum": 5, "exclusiveMinimum": True}
    s2 = {"type": "number", "minimum": 5}
    neg = {"not": {"type": "number", "maximum": 5}}
    assert is_subschema(s1, neg)
    assert not is_subschema(s2, neg)


def test_not_number_exclusive_maximum():
    # the complement of x < 5 over numbers is x >= 5
    s1 = {"type": "number", "minimum": 5}
    s2 = {"type": "number", "minimum": 4}
    neg = {"not": {"type": "number", "maximum": 5, "exclusiveMaximum": True}}
    assert is_subschema(s1, neg)
    assert not is_subschema(s2, neg)


def test_not_single_integer_value():
    # the complement of a single value contains every other number
    s1 = {"enum": [0.5]}
    s2 = {"enum": [0]}
    neg = {"not": {"enum": [0]}}
    assert is_subschema(s1, neg)
    assert not is_subschema(s2, neg)


def test_meet_integer_number_exclusive_minimum():
    # the only integer in [1, 3] greater than 2 is 3
    s1 = {
        "allOf": [
            {"type": "integer", "minimum": 1, "maximum": 3},
            {"type": "number", "minimum": 2, "exclusiveMinimum": True},
        ]
    }
    s2 = {"enum": [3]}
    assert is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_meet_integer_number_exclusive_maximum():
    # the only integer in [1, 3] less than 2 is 1
    s1 = {
        "allOf": [
            {"type": "integer", "minimum": 1, "maximum": 3},
            {"type": "number", "maximum": 2, "exclusiveMaximum": True},
        ]
    }
    s2 = {"enum": [1]}
    assert is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_meet_number_number_exclusive_bounds():
    # the meet of x >= 5 and x > 5 is x > 5, not x >= 5
    s1 = {
        "allOf": [
            {"type": "number", "minimum": 5},
            {"minimum": 5, "exclusiveMinimum": True},
        ]
    }
    s2 = {"type": "number", "minimum": 5, "exclusiveMinimum": True}
    s3 = {"type": "number", "minimum": 5}
    assert is_subschema(s1, s2)
    assert is_subschema(s2, s1)
    assert not is_subschema(s3, s1)


def test_not_bounded_integer():
    # the complement of an integer range contains the non-integer numbers
    # inside the range and all numbers outside it
    neg = {"not": {"type": "integer", "minimum": 10, "maximum": 20}}
    assert is_subschema({"enum": [10.5]}, neg)
    assert is_subschema({"enum": [9]}, neg)
    assert is_subschema({"enum": [21]}, neg)
    assert not is_subschema({"enum": [10]}, neg)
    assert not is_subschema({"enum": [20]}, neg)
    assert not is_subschema({"enum": [15]}, neg)


def test_not_unbounded_integer():
    # 10.5 validates against s1 but is not of any type in s2, while any
    # non-numeric value validates against both
    s1 = {"not": {"type": "integer"}}
    s2 = {"type": ["string", "null", "boolean", "object", "array"]}
    assert not is_subschema(s1, s2)
    assert is_subschema(s2, s1)


def test_not_integer_other_types():
    # the complement of an integer schema contains all non-numeric values
    neg = {"not": {"type": "integer"}}
    assert is_subschema({"type": "string"}, neg)
    assert is_subschema({"type": "boolean"}, neg)
    assert not is_subschema({"type": "number"}, neg)
    assert not is_subschema({"type": "integer"}, neg)
    assert is_subschema({"enum": [0.5]}, neg)
    assert not is_subschema({"enum": [0]}, neg)


def test_not_bounded_integer_number_ranges():
    # a number range is in the complement of an integer range iff it
    # contains none of the excluded integers
    neg = {"not": {"type": "integer", "minimum": 10, "maximum": 20}}
    assert is_subschema({"type": "number", "maximum": 3}, neg)
    below = {"type": "number", "maximum": 10, "exclusiveMaximum": True}
    assert is_subschema(below, neg)
    above = {"type": "number", "minimum": 20, "exclusiveMinimum": True}
    assert is_subschema(above, neg)
    assert not is_subschema({"type": "number", "maximum": 10}, neg)
    assert not is_subschema({"type": "number", "minimum": 9.5, "maximum": 10.5}, neg)
    assert is_subschema({"type": "integer", "maximum": 9}, neg)
    assert is_subschema({"type": "integer", "minimum": 21}, neg)
    assert not is_subschema({"type": "integer", "minimum": 9, "maximum": 10}, neg)
    assert not is_subschema({"type": "integer", "minimum": 10, "maximum": 20}, neg)


def test_not_integer_exclusive_bounds():
    # the excluded integers are 11..20, so 10 itself is in the complement
    neg = {
        "not": {
            "type": "integer",
            "minimum": 10,
            "exclusiveMinimum": True,
            "maximum": 20,
        }
    }
    assert is_subschema({"enum": [10]}, neg)
    assert not is_subschema({"enum": [11]}, neg)
    assert is_subschema({"enum": [21]}, neg)


def test_not_integer_only_minimum():
    # with only a lower bound, all integers above it are excluded
    neg = {"not": {"type": "integer", "minimum": 10}}
    assert is_subschema({"enum": [9]}, neg)
    assert is_subschema({"enum": [10.5]}, neg)
    assert not is_subschema({"enum": [10]}, neg)
    assert is_subschema({"type": "number", "maximum": 9.5}, neg)
    assert not is_subschema({"type": "number", "maximum": 10.5}, neg)
    assert not is_subschema({"type": "integer"}, neg)


def test_not_integer_double_negation():
    # two negations cancel out
    s = {"type": "integer", "minimum": 10, "maximum": 20}
    neg_neg = {"not": {"not": s}}
    assert is_equivalent(s, neg_neg)


def test_not_integer_self_equivalence():
    # comparing two complements exercises not-integer schemas on both sides
    s1 = {"not": {"type": "integer", "minimum": 10, "maximum": 20}}
    s2 = {"not": {"type": "integer", "minimum": 10, "maximum": 21}}
    assert is_equivalent(s1, s1)
    assert is_subschema(s2, s1)
    assert not is_subschema(s1, s2)


def test_not_single_integer_equivalent_to_number_union():
    # the complement of a single integer can also be written as a union
    # of plain number ranges plus all non-numeric types
    neg = {"not": {"type": "integer", "minimum": 5, "maximum": 5}}
    union = {
        "anyOf": [{"type": t} for t in ("string", "boolean", "null", "array", "object")]
        + [
            {"type": "number", "maximum": 5, "exclusiveMaximum": True},
            {"type": "number", "minimum": 5, "exclusiveMinimum": True},
        ]
    }
    assert is_equivalent(neg, union)


def test_not_integer_meet():
    # non-integer numbers within [0, 1]
    s1 = {
        "allOf": [
            {"not": {"type": "integer"}},
            {"type": "number", "minimum": 0, "maximum": 1},
        ]
    }
    s2 = {"type": "number", "minimum": 0, "maximum": 1}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)
    assert is_subschema({"enum": [0.5]}, s1)
    assert not is_subschema({"enum": [1]}, s1)
    assert not is_subschema({"enum": [1.5]}, s1)


def test_not_integer_meet_uninhabited():
    # the only number in [2, 2] is the integer 2, so the meet is empty
    s1 = {
        "allOf": [
            {"not": {"type": "integer"}},
            {"type": "number", "minimum": 2, "maximum": 2},
        ]
    }
    assert is_subschema(s1, {"type": "string"})


def test_not_integer_meet_integer_multiple_of():
    # every multiple of 2 is an integer, so the meet is empty
    s1 = {
        "allOf": [
            {"not": {"type": "integer"}},
            {"type": "number", "multipleOf": 2},
        ]
    }
    assert is_subschema(s1, {"type": "string"})


def test_not_integer_meet_fractional_multiple_of_is_unsupported():
    # "multiple of 0.5 but not an integer" cannot be represented
    s1 = {
        "allOf": [
            {"not": {"type": "integer"}},
            {"type": "number", "multipleOf": 0.5},
        ]
    }
    with pytest.raises(UnsupportedNegatedNumeric):
        is_subschema(s1, {"type": "number"})


def test_number_multiple_of_vs_not_integer():
    # 1.0 is a multiple of 0.5 and an integer, but the only multiple of
    # 0.5 in [0.4, 0.6] is the non-integer 0.5
    neg = {"not": {"type": "integer"}}
    assert not is_subschema({"type": "number", "multipleOf": 0.5}, neg)
    s = {"type": "number", "multipleOf": 0.5, "minimum": 0.4, "maximum": 0.6}
    assert is_subschema(s, neg)
    assert not is_subschema(
        {"type": "number", "multipleOf": 0.5, "minimum": 0.4, "maximum": 1.1}, neg
    )


def test_not_integer_union_coverage():
    # a hand-written union of "not an integer" and integer schemas covers
    # all numbers only if the integer members leave no gaps
    s1 = {"type": "number"}
    s2 = {"anyOf": [{"not": {"type": "integer"}}, {"type": "integer"}]}
    s3 = {"anyOf": [{"not": {"type": "integer"}}, {"type": "integer", "minimum": 0}]}
    assert is_subschema(s1, s2)
    assert not is_subschema(s1, s3)
    assert is_subschema({"type": "number", "minimum": 0}, s3)


def test_not_integer_enum():
    # a negated integer enum excludes exactly the enumerated integers
    neg = {"not": {"type": "integer", "enum": [5, 7]}}
    assert is_subschema({"enum": [6]}, neg)
    assert is_subschema({"enum": [5.5]}, neg)
    assert is_subschema({"enum": ["5"]}, neg)
    assert not is_subschema({"enum": [5]}, neg)
    assert not is_subschema({"enum": [7]}, neg)


def test_not_integer_in_object_property():
    # not-integer schemas work when nested inside other types
    s1 = {"type": "object", "properties": {"a": {"not": {"type": "integer"}}}}
    s2 = {"type": "object", "properties": {"a": {}}}
    assert is_subschema(s1, s2)
    assert not is_subschema(s2, s1)


def test_not_integer_meet_schemas_roundtrip():
    # the meet of "not an integer" and "number" is a schema that can be
    # fed back into the API
    m = meet_schemas({"not": {"type": "integer"}}, {"type": "number"})
    assert is_subschema(m, {"type": "number"})
    assert not is_subschema({"type": "number"}, m)
    assert is_subschema({"enum": [0.5]}, m)
    assert not is_subschema({"enum": [1]}, m)


def test_not_number_multiple_of_one():
    # "number with multipleOf 1" admits exactly the integers, so its
    # complement equals the complement of the integer type
    s1 = {"not": {"type": "number", "multipleOf": 1}}
    s2 = {"not": {"type": "integer"}}
    assert is_equivalent(s1, s2)
    neg = {"not": {"type": "number", "multipleOf": 1, "minimum": 10.5, "maximum": 20.5}}
    assert is_equivalent(
        neg, {"not": {"type": "integer", "minimum": 11, "maximum": 20}}
    )


def test_exclusive_bounds_vs_not_integer():
    # (2, 2.5] contains no integer since the bound 2 itself is excluded
    non_integer = {"allOf": [{"not": {"type": "integer"}}, {"type": "number"}]}
    s1 = {"type": "number", "minimum": 2, "exclusiveMinimum": True, "maximum": 2.5}
    s2 = {"type": "number", "minimum": 2, "maximum": 2.5}
    assert is_subschema(s1, non_integer)
    assert not is_subschema(s2, non_integer)
    # the multiples of 0.5 in (1, 1.9] are only {1.5}, but (1, 2.1] adds 2.0
    s3 = {
        "type": "number",
        "multipleOf": 0.5,
        "minimum": 1,
        "exclusiveMinimum": True,
        "maximum": 1.9,
    }
    s4 = {
        "type": "number",
        "multipleOf": 0.5,
        "minimum": 1,
        "exclusiveMinimum": True,
        "maximum": 2.1,
    }
    assert is_subschema(s3, non_integer)
    assert not is_subschema(s4, non_integer)


def test_not_integer_union_exclusive_bounds():
    # the union covers all non-integers, so only integer members matter
    union = {"anyOf": [{"not": {"type": "integer"}}, {"type": "string"}]}
    s1 = {"type": "number", "minimum": 2, "exclusiveMinimum": True, "maximum": 2.5}
    s2 = {"type": "number", "minimum": 2, "maximum": 2.5}
    assert is_subschema(s1, union)
    assert not is_subschema(s2, union)


def test_not_number_range_without_integers():
    # every integer avoids [3.2, 3.8], so integers fit its complement
    neg = {"not": {"type": "number", "minimum": 3.2, "maximum": 3.8}}
    assert is_subschema({"type": "integer"}, neg)
    assert not is_subschema({"type": "number"}, neg)
    assert not is_subschema({"enum": [3.5]}, neg)


def test_not_integer_multiple_of_is_unsupported():
    # the complement of multiples of 3 contains e.g. 4
    s1 = {"enum": [4]}
    neg = {"not": {"type": "integer", "multipleOf": 3}}
    with pytest.raises(UnsupportedNegatedNumeric):
        is_subschema(s1, neg)


def test_not_number_multiple_of_is_unsupported():
    # the complement of a multipleOf constraint contains the non-multiples,
    # which cannot be represented, so it must raise
    s1 = {"enum": [4]}
    neg = {"not": {"type": "number", "multipleOf": 2.5}}
    with pytest.raises(UnsupportedNegatedNumeric):
        is_subschema(s1, neg)


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
