# Copyright 2021 Universität Tübingen, DKFZ and EMBL
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

"""Test the core.greetings module"""

from contextlib import nullcontext
from typing import Any, Optional, Type

import pytest

from my_microservice.core.greeting import generate_greeting
from my_microservice.models import Greeting

from .fixtures.greetings import greeting_expression_fixture


@pytest.mark.parametrize(
    "language,isinformal,exception_expected",
    [
        ("Greek", True, None),
        ("Greek", False, None),
        ("Croatian", True, ValueError),
        ("Croatian", False, None),
        ("Russian", False, ValueError),
    ],
)
def test_generate_greeting(
    language: str, isinformal: bool, exception_expected: Optional[Type[Exception]]
):
    """Tests the generate_greeting function"""
    error_context: Any = (
        pytest.raises(exception_expected) if exception_expected else nullcontext()
    )
    with error_context:  # expect error if exception_expected
        with greeting_expression_fixture:  # overwrite the default GREETING_EXPRESSIONS
            greeting = generate_greeting(
                name="Friendly Tester", language=language, isinformal=isinformal
            )

        assert isinstance(greeting, Greeting)
