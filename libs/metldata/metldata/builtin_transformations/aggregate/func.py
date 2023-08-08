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
from typing import Any, Iterable, Optional

from metldata.builtin_transformations.aggregate.models import (
    MinimalClass,
    MinimalNamedSlot,
)
from metldata.transform.base import MetadataTransformationError

_FUNCTION_REGISTRY = {}


class AggregationFunction(ABC):
    """An abstract class for aggregation transformation functions"""

    @classmethod
    @abstractmethod
    def func(cls, data: Iterable[Any]) -> Any:
        """Transforms input data."""

    @classmethod
    @abstractmethod
    def result_range_name(cls) -> str:
        """Returns the name of the range of the data produced by func."""

    @classmethod
    @abstractmethod
    def result_range_cls_def(cls) -> Optional[MinimalClass]:
        """Returns the class definition of the data produced by func. None if
        the function result range is a type rather than a class."""

    @classmethod
    @abstractmethod
    def result_multivalued(cls) -> bool:
        """Returns whether or not the transformation function produces a single
        value or a list."""


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

    @classmethod
    def func(cls, data: Iterable[Any]) -> list[str]:
        return list[str](data)

    @classmethod
    def result_range_name(cls) -> str:
        return "string"

    @classmethod
    def result_range_cls_def(cls) -> Optional[MinimalClass]:
        return None

    @classmethod
    def result_multivalued(cls) -> bool:
        return True


@register_function
class StringCopyAggregation(CopyAggregation):
    """Transformation that returns a single string."""

    @classmethod
    def func(cls, data: Iterable[Any]) -> str:
        return str(cls._extract_single_value(data=data))

    @classmethod
    def result_range_name(cls) -> str:
        return "string"

    @classmethod
    def result_range_cls_def(cls) -> Optional[MinimalClass]:
        return None

    @classmethod
    def result_multivalued(cls) -> bool:
        return False


@register_function
class IntegerCopyAggregation(CopyAggregation):
    """Transformation that returns a single integer value."""

    @classmethod
    def func(cls, data: Iterable[Any]) -> int:
        return int(cls._extract_single_value(data=data))

    @classmethod
    def result_range_name(cls) -> str:
        return "integer"

    @classmethod
    def result_range_cls_def(cls) -> Optional[MinimalClass]:
        return None

    @classmethod
    def result_multivalued(cls) -> bool:
        return False


@register_function
class CountAggregation(AggregationFunction):
    """Transformation that returns the count of elements for a given sequence of
    values."""

    @classmethod
    def func(cls, data: Iterable[Any]) -> int:
        return sum(1 for _ in data)

    @classmethod
    def result_range_name(cls) -> str:
        return "integer"

    @classmethod
    def result_range_cls_def(cls) -> Optional[MinimalClass]:
        return None

    @classmethod
    def result_multivalued(cls) -> bool:
        return False


class ElementCountAggregation(AggregationFunction, ABC):
    """Aggregation that returns the counts of unique elements in the given data."""

    @classmethod
    def result_multivalued(cls) -> bool:
        return True


@register_function
class StringElementCountAggregation(ElementCountAggregation):
    """Aggregation that returns the counts of unique string elements in the
    given data."""

    @classmethod
    def func(cls, data: Iterable[Any]) -> list[dict[str, Any]]:
        return [
            {"value": str(value), "count": count}
            for value, count in Counter(data).items()
        ]

    @classmethod
    def result_range_name(cls) -> str:
        return "StringValueCount"

    @classmethod
    def result_range_cls_def(cls) -> MinimalClass:
        return MinimalClass(
            {
                MinimalNamedSlot(range="string", multivalued=False, slot_name="value"),
                MinimalNamedSlot(range="integer", multivalued=False, slot_name="count"),
            }
        )


@register_function
class IntegerElementCountAggregation(ElementCountAggregation):
    """Aggregation that returns the counts of unique integer elements in the
    given data."""

    @classmethod
    def func(cls, data: Iterable[Any]) -> list[dict[str, Any]]:
        return [
            {"value": int(value), "count": count}
            for value, count in Counter(data).items()
        ]

    @classmethod
    def result_range_name(cls) -> str:
        return "IntegerValueCount"

    @classmethod
    def result_range_cls_def(cls) -> Optional[MinimalClass]:
        return MinimalClass(
            {
                MinimalNamedSlot(range="integer", multivalued=False, slot_name="value"),
                MinimalNamedSlot(range="integer", multivalued=False, slot_name="count"),
            }
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
