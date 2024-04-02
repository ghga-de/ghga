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

"""High-level functions for deep freezing mutable objects."""

from collections.abc import Sequence
from typing import Optional

from arcticfreeze._internal._converters import (
    STANDARD_CONVERTERS,
    Converter,
)
from arcticfreeze._internal.resolve import (
    ConverterNotFoundError,  # noqa: F401 - a shortcut
    get_converter_by_type,
)


def custom_freeze(
    obj: object,
    *,
    converters: Sequence[Converter],
    by_superclass: bool = False,
) -> object:
    """Deep freeze the provided object using the provided converts. If the provided
    object is a nested data structure, it will start by freezing the lowest level
    children and then work its way up to the root object. For each child object as well
    as the root object, the object type is used to find the appropriate converter.

    Args:
        obj:
            The object to be deep frozen.
        converters:
            A sequence of converters to be used to freeze the object and its children.
        by_superclass:
            It is always tried to find a converter that matches the exact object type.
            If that fails and this argument is set to `True`, it is also tried to find a
            converter matching a superclass of the object type. The first matching
            converter is used, thus the priorities and the sequence of the converters
            are important.
            Please note that matching by superclass might cause data to be lost as a
            sub-class may define additional attributes that are not present in the
            superclass and thus not considered during the conversion. Thus by default,
            this option is set to `False`.

    Raises:
        ConverterNotFoundError:
            If no converter for the given object type could be found.
    """
    converter = get_converter_by_type(
        input_type=type(obj), converters=converters, by_superclass=by_superclass
    )

    # prepare a callable to freeze children:
    def freeze_child(child):
        return custom_freeze(child, converters=converters, by_superclass=by_superclass)

    # then freeze the object itself:
    return converter.convert(obj, freeze_child)


def freeze(
    obj: object,
    *,
    add_converters: Optional[Sequence[Converter]] = None,
    by_superclass: bool = False,
) -> object:
    """Deep freeze the provided object. If the provided object is a nested data
    structure, it will start by freezing the lowest level children and then work its
    way up to the root object. For each child object as well as the root object, the
    object type is used to find the appropriate converter.

    Args:
        obj:
            The object to be deep frozen.
        add_converters:
            Optionally provide a sequence of converters to be considered in addition
            to the standard converters that come with this library. If providing a
            custom converter for an object type that is already present in the standard
            set, the standard converter is overwritten.
        by_superclass:
            It is always tried to find a converter that matches the exact object type.
            If that fails and this argument is set to `True`, it is also tried to find a
            converter matching a superclass of the object type. The first matching
            converter is used, thus the priorities and the sequence of the converters
            (both standard and custom once defined via `add_converters`) are important.
            Please note that matching by superclass might cause data to be lost as a
            sub-class may define additional attributes that are not present in the
            superclass and thus not considered during the conversion. Thus by default,
            this option is set to `False`.

    Raises:
        ConverterNotFoundError:
            If no converter for the given object type could be found.
    """
    converters = (
        STANDARD_CONVERTERS
        if add_converters is None
        else (*STANDARD_CONVERTERS, *add_converters)
    )
    return custom_freeze(obj, converters=converters, by_superclass=by_superclass)
