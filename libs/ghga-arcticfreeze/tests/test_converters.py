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

"""Test the standard converters."""

import pytest
from arcticfreeze._internal._converters import STANDARD_CONVERTERS
from arcticfreeze._internal.resolve import sort_and_deduplicate_converters


@pytest.mark.parametrize("converters", [STANDARD_CONVERTERS])
def test_converter_sequences(converters):
    """Make sure that all builtin converters are sorted and that they only contain one
    converter for each input type.
    """
    expected_converters, _ = sort_and_deduplicate_converters(converters)
    assert expected_converters == converters
