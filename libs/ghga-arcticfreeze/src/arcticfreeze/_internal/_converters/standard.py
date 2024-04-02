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

"""Standard converters that come with this library."""

import collections
from collections.abc import Iterable, Mapping, Sequence
from typing import Callable, Final

from arcticfreeze._internal._converters.base import (
    STANDARD_MUTABLE_PRIORITY,
    STANDARD_NON_PRIMITIVE_IMMUTABLE_PRIORITY,
    STANDARD_PRIMITIVE_PRIORITY,
    Converter,
)
from arcticfreeze._internal.frozendict import FrozenDict

STANDARD_PRIMITIVE_TYPES: Final = (str, int, float, bool, type(None))


STANDARD_PRIMITIVE_CONVERTERS: Final[Sequence[Converter]] = tuple(
    Converter(input_type=type_, priority=STANDARD_PRIMITIVE_PRIORITY)
    for type_ in STANDARD_PRIMITIVE_TYPES
)


def convert_sequence(obj: Sequence, freeze_child: Callable) -> tuple:
    """A convert a sequence object."""
    return tuple(freeze_child(child) for child in obj)


def convert_set_like(obj: Iterable, freeze_child: Callable) -> set:
    """A convert a set-like object."""
    return set(freeze_child(child) for child in obj)


def convert_mapping(obj: Mapping, freeze_child: Callable) -> FrozenDict:
    """A convert a mapping object."""
    return FrozenDict(
        {freeze_child(key): freeze_child(value) for key, value in obj.items()}
    )


STANDARD_NON_PRIMITIVE_IMMUTABLE_CONVERTERS: Final[Sequence[Converter]] = (
    Converter(input_type=bytes, priority=STANDARD_NON_PRIMITIVE_IMMUTABLE_PRIORITY),
    Converter(
        input_type=tuple,
        convert=convert_sequence,
        priority=STANDARD_NON_PRIMITIVE_IMMUTABLE_PRIORITY,
    ),
    Converter(
        input_type=frozenset,
        convert=convert_set_like,
        priority=STANDARD_NON_PRIMITIVE_IMMUTABLE_PRIORITY,
    ),
    Converter(
        input_type=FrozenDict,
        convert=convert_mapping,
        priority=STANDARD_NON_PRIMITIVE_IMMUTABLE_PRIORITY,
    ),
)

STANDARD_MUTABLE_CONVERTERS: Final[Sequence[Converter]] = (
    Converter(
        input_type=list, convert=convert_sequence, priority=STANDARD_MUTABLE_PRIORITY
    ),
    Converter(
        input_type=dict,
        convert=convert_mapping,
        priority=STANDARD_MUTABLE_PRIORITY,
    ),
    Converter(
        input_type=set, convert=convert_set_like, priority=STANDARD_MUTABLE_PRIORITY
    ),
    Converter(
        input_type=collections.deque,
        convert=convert_sequence,
        priority=STANDARD_MUTABLE_PRIORITY,
    ),
)

STANDARD_CONVERTERS: Final = (
    *STANDARD_PRIMITIVE_CONVERTERS,
    *STANDARD_NON_PRIMITIVE_IMMUTABLE_CONVERTERS,
    *STANDARD_MUTABLE_CONVERTERS,
)
