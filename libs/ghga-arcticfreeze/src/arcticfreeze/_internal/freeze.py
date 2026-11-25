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

"""High-level functions for deep freezing mutable objects."""

from collections.abc import Callable, Sequence
from typing import Final

from arcticfreeze._internal._converters import (
    STANDARD_CONVERTERS,
    Converter,
)
from arcticfreeze._internal._converters.standard import STANDARD_PRIMITIVE_TYPES
from arcticfreeze._internal.errors import (
    MaxDepthExceededError,
    ReferenceCycleError,
)
from arcticfreeze._internal.resolve import ConverterResolver

DEFAULT_MAX_DEPTH: Final = 100

# Objects of these types have no children, so they are neither tracked for cycles
# nor memoized, which would only cost time and memory:
_ATOMIC_TYPES: Final = frozenset((*STANDARD_PRIMITIVE_TYPES, bytes))

# Marks a memo entry whose object is still being frozen:
_IN_PROGRESS: Final = object()


class _Freezer:
    """Freezes one object tree, keeping the state of that one run.

    The memo maps the id of each visited object to the object and its frozen result.
    It keeps the object alive, so that its id cannot be reused by a temporary object
    that a converter creates and drops during the same run.
    """

    def __init__(
        self,
        *,
        converters: Sequence[Converter],
        by_superclass: bool,
        max_depth: int | None,
    ):
        self._resolver = ConverterResolver(
            converters=converters, by_superclass=by_superclass
        )
        self._max_depth = max_depth
        self._memo: dict[int, tuple[object, object]] = {}

    def freeze(self, obj: object, depth: int) -> object:
        """Freeze an object found at the given nesting depth."""
        if self._max_depth is not None and depth > self._max_depth:
            raise MaxDepthExceededError(max_depth=self._max_depth)

        input_type = type(obj)
        converter = self._resolver.resolve(input_type)
        freeze_child = self._child_freezer(depth + 1)

        if input_type in _ATOMIC_TYPES:
            return converter.convert(obj, freeze_child)

        key = id(obj)
        entry = self._memo.get(key)
        if entry is not None:
            frozen = entry[1]
            if frozen is _IN_PROGRESS:
                raise ReferenceCycleError(input_type=input_type)
            return frozen

        self._memo[key] = (obj, _IN_PROGRESS)
        frozen = converter.convert(obj, freeze_child)
        self._memo[key] = (obj, frozen)
        return frozen

    def _child_freezer(self, depth: int) -> Callable[[object], object]:
        """Get the callable that converters use to freeze their children."""
        return lambda child: self.freeze(child, depth)


def custom_freeze(
    obj: object,
    *,
    converters: Sequence[Converter],
    by_superclass: bool = False,
    max_depth: int | None = DEFAULT_MAX_DEPTH,
) -> object:
    """Deep freeze the provided object using the provided converts. If the provided
    object is a nested data structure, it will start by freezing the lowest level
    children and then work its way up to the root object. For each child object as well
    as the root object, the object type is used to find the appropriate converter.

    An object that occurs more than once in the structure is frozen only once, and
    all its occurrences share the frozen result.

    Args:
        obj:
            The object to be deep frozen.
        converters:
            A sequence of converters to be used to freeze the object and its children.
            If several converters have the same input type, the last one is used.
        by_superclass:
            It is always tried to find a converter that matches the exact object type.
            If that fails and this argument is set to `True`, it is also tried to find a
            converter matching a superclass of the object type. The converter with the
            highest priority among the matching ones is used, and among equal
            priorities the one defined first.
            Please note that matching by superclass might cause data to be lost as a
            sub-class may define additional attributes that are not present in the
            superclass and thus not considered during the conversion. Thus by default,
            this option is set to `False`.
        max_depth:
            The maximum nesting depth of the object, where the children of the root
            object are at depth 1. It bounds the recursion, so that deeply nested
            untrusted input fails with a `MaxDepthExceededError` instead of exhausting
            the call stack. Pass `None` to be limited only by the recursion limit.

    Raises:
        ConverterNotFoundError:
            If no converter for the given object type could be found.
        MaxDepthExceededError:
            If the object is nested deeper than `max_depth`, or so deeply that the
            recursion limit is reached first.
        ReferenceCycleError:
            If the object contains itself, directly or through its children.
    """
    if max_depth is not None and max_depth < 0:
        raise ValueError("The maximum depth must not be negative.")

    freezer = _Freezer(
        converters=converters, by_superclass=by_superclass, max_depth=max_depth
    )
    try:
        return freezer.freeze(obj, 0)
    except RecursionError as error:
        # The stack can run out before max_depth is reached, if the caller's stack is
        # already deep, the recursion limit is low, or a converter calls freeze again:
        raise MaxDepthExceededError(max_depth=None) from error


def freeze(
    obj: object,
    *,
    add_converters: Sequence[Converter] | None = None,
    by_superclass: bool = False,
    max_depth: int | None = DEFAULT_MAX_DEPTH,
) -> object:
    """Deep freeze the provided object. If the provided object is a nested data
    structure, it will start by freezing the lowest level children and then work its
    way up to the root object. For each child object as well as the root object, the
    object type is used to find the appropriate converter.

    An object that occurs more than once in the structure is frozen only once, and
    all its occurrences share the frozen result.

    Args:
        obj:
            The object to be deep frozen.
        add_converters:
            Optionally provide a sequence of converters to be considered in addition
            to the standard converters that come with this library. If providing a
            custom converter for an object type that is already present in the standard
            set, the standard converter is overwritten, whatever their priorities.
        by_superclass:
            It is always tried to find a converter that matches the exact object type.
            If that fails and this argument is set to `True`, it is also tried to find a
            converter matching a superclass of the object type. The converter with the
            highest priority among the matching ones is used, and among equal
            priorities the one defined first (standard converters come before the
            ones defined via `add_converters`).
            Please note that matching by superclass might cause data to be lost as a
            sub-class may define additional attributes that are not present in the
            superclass and thus not considered during the conversion. Thus by default,
            this option is set to `False`.
        max_depth:
            The maximum nesting depth of the object, where the children of the root
            object are at depth 1. It bounds the recursion, so that deeply nested
            untrusted input fails with a `MaxDepthExceededError` instead of exhausting
            the call stack. Pass `None` to be limited only by the recursion limit.

    Raises:
        ConverterNotFoundError:
            If no converter for the given object type could be found.
        MaxDepthExceededError:
            If the object is nested deeper than `max_depth`, or so deeply that the
            recursion limit is reached first.
        ReferenceCycleError:
            If the object contains itself, directly or through its children.

    All three exceptions subclass `FreezeError`, which is a `ValueError`, so that
    Pydantic reports them as validation errors when `freeze` runs in a validator.
    """
    converters = (
        STANDARD_CONVERTERS
        if add_converters is None
        else (*STANDARD_CONVERTERS, *add_converters)
    )
    return custom_freeze(
        obj, converters=converters, by_superclass=by_superclass, max_depth=max_depth
    )
