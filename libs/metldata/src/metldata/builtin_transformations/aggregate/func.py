# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
#

"""Transformation and aggregation functions for the aggregate module."""

from abc import ABC, abstractmethod
from collections import Counter
from collections.abc import Iterable
from operator import itemgetter
from typing import Any, Optional

from metldata.builtin_transformations.aggregate.models import (
    MinimalClass,
    MinimalNamedSlot,
)
from metldata.transform.base import MetadataTransformationError

_FUNCTION_REGISTRY = {}


class AggregationFunction(ABC):
    """An abstract class for aggregation transformation functions"""

    result_range_name: str
    """The name of the range of the data produced by func."""

    result_range_cls_def: Optional[MinimalClass]
    """The class definition of the data produced by func. None if the function
    result range is a type rather than a class."""

    result_multivalued: bool
    """Whether or not the transformation function produces a single value or a
    list."""

    @classmethod
    @abstractmethod
    def func(cls, data: Iterable[Any]) -> Any:
        """Transforms input data."""


def register_function(func: type[AggregationFunction]) -> type[AggregationFunction]:
    """Registers a function in the aggregation function registry."""
    _FUNCTION_REGISTRY[func.__name__] = func
    return func


class CopyAggregation(AggregationFunction, ABC):
    """An abstract base class for type-specific copy aggregation functions."""

    @classmethod
    def _extract_single_value(cls, data: Iterable[Any]) -> Any:
        iterator = iter(data)
        value = next(iterator)
        try:
            next(iterator)
        except StopIteration:
            return value
        raise MetadataTransformationError(
            "Multiple values passed to copy aggregation function where only a"
            " single value was expected."
        )


@register_function
class StringListCopyAggregation(CopyAggregation):
    """Transformation that returns a list of strings."""

    result_range_name = "string"
    result_range_cls_def = None
    result_multivalued = True

    @classmethod
    def func(cls, data: Iterable[Any]) -> list[str]:
        return list[str](data)


@register_function
class StringCopyAggregation(CopyAggregation):
    """Transformation that returns a single string."""

    result_range_name = "string"
    result_range_cls_def = None
    result_multivalued = False

    @classmethod
    def func(cls, data: Iterable[Any]) -> str:
        return str(cls._extract_single_value(data=data))


@register_function
class IntegerCopyAggregation(CopyAggregation):
    """Transformation that returns a single integer value."""

    result_range_name = "integer"
    result_range_cls_def = None
    result_multivalued = False

    @classmethod
    def func(cls, data: Iterable[Any]) -> int:
        return int(cls._extract_single_value(data=data))


@register_function
class CountAggregation(AggregationFunction):
    """Transformation that returns the count of elements for a given sequence of
    values.
    """

    result_range_name = "integer"
    result_range_cls_def = None
    result_multivalued = False

    @classmethod
    def func(cls, data: Iterable[Any]) -> int:
        return sum(1 for _ in data)


@register_function
class IntegerSumAggregation(AggregationFunction):
    """Transformation that returns the sum for a given sequence of integer
    values.
    """

    result_range_name = "integer"
    result_range_cls_def = None
    result_multivalued = False

    @classmethod
    def func(cls, data: Iterable[int]) -> int:
        return sum(data)


class ElementCountAggregation(AggregationFunction, ABC):
    """Aggregation that returns the counts of unique elements in the given data."""

    result_multivalued = True


@register_function
class StringElementCountAggregation(ElementCountAggregation):
    """Aggregation that returns the counts of unique string elements in the
    given data.
    """

    result_range_name = "StringValueCount"
    result_range_cls_def = MinimalClass(
        {
            MinimalNamedSlot(range="string", multivalued=False, slot_name="value"),
            MinimalNamedSlot(range="integer", multivalued=False, slot_name="count"),
        }
    )

    @classmethod
    def func(cls, data: Iterable[Any]) -> list[dict[str, Any]]:
        return sorted(
            (
                {"value": "unknown" if value is None else str(value), "count": count}
                for value, count in Counter(data).items()
            ),
            key=itemgetter("value"),
        )


@register_function
class IntegerElementCountAggregation(ElementCountAggregation):
    """Aggregation that returns the counts of unique integer elements in the
    given data.
    """

    result_range_name = "IntegerValueCount"
    result_range_cls_def = MinimalClass(
        {
            MinimalNamedSlot(range="integer", multivalued=False, slot_name="value"),
            MinimalNamedSlot(range="integer", multivalued=False, slot_name="count"),
        }
    )

    @classmethod
    def func(cls, data: Iterable[Any]) -> list[dict[str, Any]]:
        return sorted(
            (
                {"value": int(value), "count": count}
                for value, count in Counter(data).items()
                if value is not None
            ),
            key=itemgetter("value"),
        )


def transformation_by_name(name: str) -> type[AggregationFunction]:
    """Returns a transformation class type based on the transformation class name.

    Args:
        name (str): The transformation class name

    Raises:
        KeyError: If 'name' cannot be resolved to a known transformation class.

    Returns:
        type: The transformation class type
    """
    return _FUNCTION_REGISTRY[name + "Aggregation"]
