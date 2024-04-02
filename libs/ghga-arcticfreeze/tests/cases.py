# Copyright 2024 Kersten Henrik Breuer
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test cases describing input and expected output."""

from dataclasses import dataclass
from typing import Any

from arcticfreeze import ConverterNotFoundError, FrozenDict


@dataclass(frozen=True)
class ValidTestCase:
    """A test case describing valid inputs and expected outputs when freezing."""

    name: str
    inputs: object
    expected_outputs: object


@dataclass(frozen=True)
class InvalidTestCase:
    """A test case describing invalid inputs that should raise an exception when
    freezing.
    """

    name: str
    inputs: object
    expected_exception_type: type[Exception]


SEQUENCE_OF_PRIMITIVES_EXAMPLE = (1, "hello", True, None, b"hello")
MAPPING_OF_PRIMITIVES_EXAMPLE = {
    value: value for value in SEQUENCE_OF_PRIMITIVES_EXAMPLE
}
NESTED_IMMUTABLE_EXAMPLE: Any = FrozenDict(
    {"a": tuple(frozenset(SEQUENCE_OF_PRIMITIVES_EXAMPLE))}
)

VALID_CASES = (
    # Single primitive values:
    ValidTestCase(
        name="primitive_str",
        inputs="hello",
        expected_outputs="hello",
    ),
    ValidTestCase(
        name="primitive_int",
        inputs=42,
        expected_outputs=42,
    ),
    ValidTestCase(
        name="primitive_float",
        inputs=3.14,
        expected_outputs=3.14,
    ),
    ValidTestCase(
        name="primitive_bool",
        inputs=True,
        expected_outputs=True,
    ),
    ValidTestCase(
        name="primitive_none",
        inputs=None,
        expected_outputs=None,
    ),
    # Empty non-primitive values:
    ValidTestCase(
        name="empty_tuple",
        inputs=(),
        expected_outputs=(),
    ),
    ValidTestCase(
        name="empty_FrozenDict",
        inputs=FrozenDict(),
        expected_outputs=FrozenDict(),
    ),
    ValidTestCase(
        name="empty_frozenset",
        inputs=frozenset(),
        expected_outputs=frozenset(),
    ),
    ValidTestCase(
        name="empty_list",
        inputs=[],
        expected_outputs=(),
    ),
    ValidTestCase(
        name="empty_dict",
        inputs={},
        expected_outputs=FrozenDict(),
    ),
    ValidTestCase(
        name="empty_set",
        inputs=set(),
        expected_outputs=frozenset(),
    ),
    # Fully immutable non-primitive values
    ValidTestCase(
        name="tuple_of_primitives",
        inputs=tuple(SEQUENCE_OF_PRIMITIVES_EXAMPLE),
        expected_outputs=tuple(SEQUENCE_OF_PRIMITIVES_EXAMPLE),
    ),
    ValidTestCase(
        name="FrozenDict_of_primitives",
        inputs=FrozenDict(MAPPING_OF_PRIMITIVES_EXAMPLE),
        expected_outputs=FrozenDict(MAPPING_OF_PRIMITIVES_EXAMPLE),
    ),
    ValidTestCase(
        name="frozenset_of_primitives",
        inputs=frozenset(SEQUENCE_OF_PRIMITIVES_EXAMPLE),
        expected_outputs=frozenset(SEQUENCE_OF_PRIMITIVES_EXAMPLE),
    ),
    # Mutable non-primitive values:
    ValidTestCase(
        name="list_of_primitives",
        inputs=list(SEQUENCE_OF_PRIMITIVES_EXAMPLE),
        expected_outputs=tuple(SEQUENCE_OF_PRIMITIVES_EXAMPLE),
    ),
    ValidTestCase(
        name="dict_of_primitives",
        inputs=dict(MAPPING_OF_PRIMITIVES_EXAMPLE),
        expected_outputs=FrozenDict(MAPPING_OF_PRIMITIVES_EXAMPLE),
    ),
    ValidTestCase(
        name="set_of_primitives",
        inputs=set(SEQUENCE_OF_PRIMITIVES_EXAMPLE),
        expected_outputs=frozenset(SEQUENCE_OF_PRIMITIVES_EXAMPLE),
    ),
    # Nested values:
    ValidTestCase(
        name="nested_fully_immutable",
        inputs=NESTED_IMMUTABLE_EXAMPLE,
        expected_outputs=NESTED_IMMUTABLE_EXAMPLE,
    ),
    ValidTestCase(
        name="nested_mutable_parent_immutable_children",
        inputs={"a": tuple(frozenset(SEQUENCE_OF_PRIMITIVES_EXAMPLE))},
        expected_outputs=NESTED_IMMUTABLE_EXAMPLE,
    ),
    ValidTestCase(
        name="nested_immutable_parent_mutable_children",
        inputs=FrozenDict({"a": list(set(SEQUENCE_OF_PRIMITIVES_EXAMPLE))}),
        expected_outputs=NESTED_IMMUTABLE_EXAMPLE,
    ),
    ValidTestCase(
        name="nested_fully_mutable",
        inputs={"a": list(set(SEQUENCE_OF_PRIMITIVES_EXAMPLE))},
        expected_outputs=NESTED_IMMUTABLE_EXAMPLE,
    ),
)

unkown_value = object()

INVALID_CASES = (
    InvalidTestCase(
        name="unkown_single_value",
        inputs=unkown_value,
        expected_exception_type=ConverterNotFoundError,
    ),
    InvalidTestCase(
        name="tuple_of_unkowns",
        inputs=(unkown_value,),
        expected_exception_type=ConverterNotFoundError,
    ),
    InvalidTestCase(
        name="nested_unkowns_children",
        inputs={"a": ({unkown_value})},
        expected_exception_type=ConverterNotFoundError,
    ),
)
