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

"""Functionality for resolving the converter matching a given object."""

from collections.abc import Mapping, Sequence

from arcticfreeze._internal._converters import Converter


class ConverterNotFoundError(Exception):
    """An exception indicating that a converter for a given type could not be found."""

    def __init__(self, *, input_type: type):
        super().__init__(
            f"No converter was found freezing an object of type {input_type}."
        )


def sort_and_deduplicate_converters(
    converters: Sequence[Converter],
) -> tuple[Sequence[Converter], Mapping[type, Converter]]:
    """The provided sequence of converters is sorted (1) by decreasing priority and (2)
    by the order in which they where originally defined. For each object type, only the
    last converter in the sorted sequence is kept. The function returns a tuple of the
    sorted sequence of converters and a mapping of sorted converters by object type.
    """
    sorted_converters = sorted(
        converters, key=lambda converter: converter.priority, reverse=True
    )
    converters_by_input_type = {
        converter.input_type: converter for converter in sorted_converters
    }
    sorted_deduplicated_converters = tuple(converters_by_input_type.values())
    return sorted_deduplicated_converters, converters_by_input_type


def get_converter_by_type(
    *,
    input_type: type,
    converters: Sequence[Converter],
    by_superclass: bool = True,
) -> Converter:
    """Get the converter for the given object type.

    Args:
        input_type:
            The type of the object to be converted.
        converters:
            A sequence of converters, see the documentation of the `custom_freeze`
            function for details.
        by_superclass:
            Consider superclasses for matching converter, see the documentation of the
            `freeze` function for details.

    Raises:
        ConverterNotFoundError:
            If no converter for the given object type could be found.
    """
    converters, converters_by_input_type = sort_and_deduplicate_converters(converters)

    # try to match by exact type:
    try:
        return converters_by_input_type[input_type]
    except KeyError as error:
        if not by_superclass:
            raise ConverterNotFoundError(input_type=input_type) from error

    # match by superclass:
    for converter in converters:
        if issubclass(input_type, converter.input_type):
            return converter

    raise ConverterNotFoundError(input_type=input_type)
