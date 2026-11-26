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

"""Functionality for resolving the converter matching a given object."""

from collections.abc import Mapping, Sequence

from arcticfreeze._internal._converters import Converter
from arcticfreeze._internal.errors import ConverterNotFoundError


def sort_and_deduplicate_converters(
    converters: Sequence[Converter],
) -> tuple[Sequence[Converter], Mapping[type, Converter]]:
    """Deduplicate and sort the provided sequence of converters.

    For each object type, only the converter defined last is kept, so a custom
    converter replaces a standard one for the same type whatever their priorities.
    The remaining converters are sorted by decreasing priority and, among equal
    priorities, by the order in which they were defined; matching by superclass
    follows this order. The function returns a tuple of the sorted sequence of
    converters and a mapping of these converters by object type.
    """
    converters_by_input_type = {
        converter.input_type: converter for converter in converters
    }
    sorted_converters = tuple(
        sorted(
            converters_by_input_type.values(),
            key=lambda converter: converter.priority,
            reverse=True,
        )
    )
    return sorted_converters, {
        converter.input_type: converter for converter in sorted_converters
    }


class ConverterResolver:
    """Resolves the converter for an object type.

    The converters are sorted and deduplicated once on construction, and each
    resolved type is cached, so that freezing a large object does not repeat this
    work for every node.
    """

    def __init__(self, *, converters: Sequence[Converter], by_superclass: bool):
        """Prepare the lookup.

        Args:
            converters:
                A sequence of converters, see the documentation of the
                `custom_freeze` function for details.
            by_superclass:
                Consider superclasses for matching converter, see the documentation
                of the `freeze` function for details.
        """
        self._sorted_converters, converters_by_input_type = (
            sort_and_deduplicate_converters(converters)
        )
        self._cache: dict[type, Converter] = dict(converters_by_input_type)
        self._by_superclass = by_superclass

    def resolve(self, input_type: type) -> Converter:
        """Get the converter for the given object type.

        Raises:
            ConverterNotFoundError:
                If no converter for the given object type could be found.
        """
        try:
            return self._cache[input_type]
        except KeyError as error:
            if not self._by_superclass:
                raise ConverterNotFoundError(input_type=input_type) from error

        for converter in self._sorted_converters:
            if issubclass(input_type, converter.input_type):
                self._cache[input_type] = converter
                return converter

        raise ConverterNotFoundError(input_type=input_type)
