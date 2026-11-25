# Copyright 2024 Kersten Henrik Breuer
#
# Modifications Copyright 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)
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

"""Test the freeze function."""

import sys
from collections.abc import Callable
from typing import Annotated, Any

import pytest
from pydantic import BaseModel, BeforeValidator, ValidationError

from arcticfreeze import (
    DEFAULT_MAX_DEPTH,
    Converter,
    ConverterNotFoundError,
    FreezeError,
    MaxDepthExceededError,
    ReferenceCycleError,
    freeze,
)
from tests.cases import INVALID_CASES, VALID_CASES, InvalidTestCase, ValidTestCase


@pytest.mark.parametrize(
    "test_case",
    VALID_CASES,
    ids=lambda test_case: test_case.name,
)
def test_valid_inputs(test_case: ValidTestCase):
    """Test the arctic freeze function with valid inputs."""
    observed_outputs = freeze(test_case.inputs)

    assert observed_outputs == test_case.expected_outputs
    # Equality alone is not enough, as e.g. `set(...) == frozenset(...)` holds even
    # though only the latter is immutable:
    assert type(observed_outputs) is type(test_case.expected_outputs)


@pytest.mark.parametrize(
    "test_case",
    INVALID_CASES,
    ids=lambda test_case: test_case.name,
)
def test_invalid_inputs(test_case: InvalidTestCase):
    """Test the arctic freeze function with invalid inputs."""
    with pytest.raises(test_case.expected_exception_type):
        freeze(test_case.inputs)


def _nest(depth: int, container: type = list) -> object:
    """Build a structure whose innermost object is at the given depth."""
    obj: object = 1
    for _ in range(depth):
        obj = [obj] if container is list else {"a": obj}
    return obj


@pytest.mark.parametrize("container", [list, dict])
def test_max_depth_reached(container: type):
    """An object nested exactly to the maximum depth is frozen."""
    assert freeze(_nest(DEFAULT_MAX_DEPTH, container)) == freeze(
        _nest(DEFAULT_MAX_DEPTH, container), max_depth=None
    )
    freeze(_nest(5, container), max_depth=5)


@pytest.mark.parametrize("container", [list, dict])
def test_max_depth_exceeded(container: type):
    """An object nested deeper than the maximum depth is rejected."""
    with pytest.raises(MaxDepthExceededError, match="more than 100 levels") as info:
        freeze(_nest(DEFAULT_MAX_DEPTH + 1, container))
    assert info.value.max_depth == DEFAULT_MAX_DEPTH

    with pytest.raises(MaxDepthExceededError, match="more than 5 levels"):
        freeze(_nest(6, container), max_depth=5)

    with pytest.raises(MaxDepthExceededError):
        freeze([1], max_depth=0)


def test_max_depth_disabled():
    """Without a maximum depth, nesting is limited only by the recursion limit, which
    still fails with a MaxDepthExceededError instead of a RecursionError.
    """
    freeze(_nest(DEFAULT_MAX_DEPTH + 50), max_depth=None)

    with pytest.raises(MaxDepthExceededError, match="recursion limit") as info:
        freeze(_nest(sys.getrecursionlimit()), max_depth=None)
    assert info.value.max_depth is None
    assert isinstance(info.value.__cause__, RecursionError)


def test_max_depth_negative():
    """A negative maximum depth is rejected."""
    with pytest.raises(ValueError, match="must not be negative"):
        freeze(1, max_depth=-1)


def test_reference_cycle():
    """An object that contains itself is rejected, also when max_depth is None."""
    cyclic_list: list = [1]
    cyclic_list.append(cyclic_list)
    with pytest.raises(ReferenceCycleError, match="list"):
        freeze(cyclic_list, max_depth=None)

    cyclic_dict: dict = {"a": {}}
    cyclic_dict["a"]["b"] = [cyclic_dict]
    with pytest.raises(ReferenceCycleError, match="dict"):
        freeze(cyclic_dict)


def test_shared_object_frozen_once():
    """An object that occurs several times is frozen once and shared, so repeated
    references, as produced by YAML aliases, do not multiply the work.
    """
    calls = 0

    def convert_list(obj: list, freeze_child: Callable) -> tuple:
        nonlocal calls
        calls += 1
        return tuple(freeze_child(child) for child in obj)

    shared = [1, 2]
    level: list = [shared]
    for _ in range(20):
        level = [level] * 10  # 10**20 paths, without the memo

    frozen = freeze(level, add_converters=[Converter(list, convert_list)])
    assert calls == 22
    assert isinstance(frozen, tuple)
    assert frozen[0] is frozen[1]


def test_temporary_objects_not_confused():
    """A converter may pass temporary objects to freeze_child; one dropped temporary
    must not be confused with the next one that gets the same id.
    """

    class Point:
        def __init__(self, x: int, y: int):
            self.x = x
            self.y = y

    point_converter = Converter(
        input_type=Point,
        convert=lambda obj, freeze_child: freeze_child([obj.x, obj.y]),
    )
    points = [Point(i, -i) for i in range(1000)]

    frozen = freeze(points, add_converters=[point_converter])
    assert frozen == tuple((i, -i) for i in range(1000))


@pytest.mark.parametrize(
    "value, error_type",
    [
        (object(), ConverterNotFoundError),
        (_nest(DEFAULT_MAX_DEPTH + 1), MaxDepthExceededError),
    ],
)
def test_errors_are_value_errors(value: object, error_type: type[Exception]):
    """Freeze errors subclass ValueError, so Pydantic reports them as validation
    errors when freeze runs in a validator.
    """

    class Model(BaseModel):
        value: Annotated[Any, BeforeValidator(lambda obj: freeze(obj))]

    with pytest.raises(error_type) as info:
        freeze(value)
    assert isinstance(info.value, FreezeError)
    assert isinstance(info.value, ValueError)

    with pytest.raises(ValidationError, match="Value error"):
        Model(value=value)


@pytest.mark.parametrize("shared_first", [True, False])
def test_shared_object_depth_counted_everywhere(shared_first: bool):
    """A shared object counts at its deepest occurrence, whichever comes first, so
    reusing its frozen result cannot exceed the maximum depth.
    """
    shared = _nest(50)
    deeper: object = shared
    for _ in range(60):
        deeper = [deeper]
    items = [shared, deeper] if shared_first else [deeper, shared]
    with pytest.raises(MaxDepthExceededError):
        freeze(items)


class _Box:
    """A custom container whose converter skips children it cannot freeze."""

    def __init__(self, *payload: object):
        self.payload = payload


def _convert_box_skipping_errors(obj: _Box, freeze_child: Callable) -> tuple:
    """Freeze the children of a box, replacing those without a converter."""
    frozen = []
    for child in obj.payload:
        try:
            frozen.append(freeze_child(child))
        except ConverterNotFoundError:
            frozen.append("?")
    return tuple(frozen)


_BOX_CONVERTER = Converter(_Box, _convert_box_skipping_errors)


@pytest.mark.parametrize("shared_first", [True, False])
def test_converter_catching_child_error_keeps_depth(shared_first: bool):
    """A converter that catches a child's error leaves the depth of its object
    intact, so reusing the object later still counts its full depth.
    """
    box = _Box(_nest(50), [object()])
    deeper: object = box
    for _ in range(60):
        deeper = [deeper]
    items = [box, deeper] if shared_first else [deeper, box]
    with pytest.raises(MaxDepthExceededError):
        freeze(items, add_converters=[_BOX_CONVERTER])


def test_converter_catching_child_error_no_false_cycle():
    """A child whose freezing failed is not mistaken for a cycle when it occurs
    again.
    """
    failing = [object()]
    frozen = freeze(_Box(failing, failing), add_converters=[_BOX_CONVERTER])
    assert frozen == ("?", "?")
