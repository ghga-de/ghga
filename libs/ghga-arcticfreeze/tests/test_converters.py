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

"""Test the standard converters."""

import pytest

from arcticfreeze import Converter, freeze
from arcticfreeze._internal._converters import STANDARD_CONVERTERS
from arcticfreeze._internal.resolve import sort_and_deduplicate_converters


@pytest.mark.parametrize("converters", [STANDARD_CONVERTERS])
def test_converter_sequences(converters):
    """Make sure that all builtin converters are sorted and that they only contain one
    converter for each input type.
    """
    expected_converters, _ = sort_and_deduplicate_converters(converters)
    assert expected_converters == converters


@pytest.mark.parametrize("priority", [-1000, 0, 1000])
@pytest.mark.parametrize("input_value", [[1], "text", {"a": 1}])
def test_custom_converter_replaces_standard(priority: int, input_value: object):
    """A custom converter for a type that has a standard converter is used instead of
    it, whatever the priorities.
    """
    custom = Converter(
        input_type=type(input_value),
        convert=lambda obj, freeze_child: "custom",
        priority=priority,
    )
    assert freeze(input_value, add_converters=[custom]) == "custom"


def test_superclass_match_by_priority():
    """Matching by superclass uses the matching converter with the highest priority,
    and the one defined first among equal priorities.
    """

    class Base:
        pass

    class Middle(Base):
        pass

    class Leaf(Middle):
        pass

    def converter(input_type: type, result: str, priority: int) -> Converter:
        return Converter(input_type, lambda obj, _: result, priority)

    low_base = converter(Base, "base", -10)
    high_middle = converter(Middle, "middle", 10)
    assert (
        freeze(Leaf(), add_converters=[low_base, high_middle], by_superclass=True)
        == "middle"
    )
    high_base = converter(Base, "base", 10)
    assert (
        freeze(Leaf(), add_converters=[high_base, high_middle], by_superclass=True)
        == "base"
    )
