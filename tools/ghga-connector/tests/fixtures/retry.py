# Copyright 2021 - 2022 Universität Tübingen, DKFZ and EMBL
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
from typing import Callable, Generator, Optional

import pytest

from ghga_connector.core.retry import WithRetry


class RetryFixture:
    """A helper class to get and set (overwrite) ."""

    @property
    def max_retries(self) -> Optional[int]:
        """returns the current max_retries value"""
        return WithRetry._max_retries

    @max_retries.setter
    def max_retries(self, value: int):
        """Overwrite the default value of max_retries"""
        WithRetry._max_retries = value


def retry_fixure_factory(
    default_retries: Optional[int],
) -> Callable[[], Generator[RetryFixture, None, None]]:
    """
    Creates a fixture with a default value for the max_retries parameter.
    """

    @pytest.fixture
    def fixture() -> Generator[RetryFixture, None, None]:
        """
        Fixture dealing with cleanup for all tests touching functions
        annotated with the 'WithRetry' class decorator.
        Those tests need to request this fixture and use 'WithRetry.set_retries'.
        """
        # set the max_retries default value for testing:
        WithRetry._max_retries = default_retries

        # provide functionality to set/read/overwrite the max_retries param:
        yield RetryFixture()

        # Resets the max_retries parameter to `None`:
        WithRetry._max_retries = None

    return fixture


retry_fixture = retry_fixure_factory(None)
zero_retry_fixture = retry_fixure_factory(0)
