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
from typing import Any, Optional, Sequence

from metldata.builtin_transformations.aggregate.models import (
    MinimalClass,
    MinimalNamedSlot,
)


class AggregationFunction(ABC):
    """An abstract class for aggregation transformation functions"""

    @classmethod
    @abstractmethod
    def func(cls, data: Any) -> Any:
        """Transforms input data."""

    @classmethod
    @abstractmethod
    def result_range(cls) -> tuple[str, Optional[MinimalClass]]:
        """Returns the range of the data produced by func."""

    @classmethod
    @abstractmethod
    def result_multivalued(cls) -> bool:
        """Returns whether or not the transformation function produces a single
        value or a list."""


class CountAggregation(AggregationFunction):
    """Transformation that returns the count of elements for a given sequence of
    values."""

    @classmethod
    def func(cls, data: Sequence[Any]) -> int:
        return len(data)

    @classmethod
    def result_range(cls) -> tuple[str, Optional[MinimalClass]]:
        return "integer", None

    @classmethod
    def result_multivalued(cls) -> bool:
        return False


class ElementCountAggregation(AggregationFunction, ABC):
    """Aggregation that returns the counts of unique elements in the given data."""

    @classmethod
    def result_multivalued(cls) -> bool:
        return True


class StringElementCountAggregation(ElementCountAggregation):
    """Aggregation that returns the counts of unique string elements in the
    given data."""

    @classmethod
    def func(cls, data: Sequence[Any]) -> list[dict[str, Any]]:
        return [
            {"value": str(value), "count": count}
            for value, count in Counter(data).items()
        ]

    @classmethod
    def result_range(cls) -> tuple[str, Optional[MinimalClass]]:
        return "StringValueCount", MinimalClass(
            {
                MinimalNamedSlot(range="string", multivalued=False, slot_name="value"),
                MinimalNamedSlot(range="integer", multivalued=False, slot_name="count"),
            }
        )


class IntegerElementCountAggregation(ElementCountAggregation):
    """Aggregation that returns the counts of unique integer elements in the
    given data."""

    @classmethod
    def func(cls, data: Sequence[Any]) -> list[dict[str, Any]]:
        return [
            {"value": int(value), "count": count}
            for value, count in Counter(data).items()
        ]

    @classmethod
    def result_range(cls) -> tuple[str, Optional[MinimalClass]]:
        return "IntegerValueCount", MinimalClass(
            {
                MinimalNamedSlot(range="integer", multivalued=False, slot_name="value"),
                MinimalNamedSlot(range="integer", multivalued=False, slot_name="count"),
            }
        )


def transformation_by_name(name: str) -> type:
    """Returns a transformation class type based on the transformation class name.

    Args:
        name (str): The transformation class name

    Raises:
        KeyError: If 'name' cannot be resolved to a known transformation class.

    Returns:
        type: The transformation class type
    """
    trans_type = globals()[name + "Aggregation"]
    if not issubclass(trans_type, AggregationFunction):
        raise KeyError(name)
    return trans_type
