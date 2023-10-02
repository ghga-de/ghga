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

"""Test the core application."""

from pytest import fixture, mark

from auth_demo.core import Hangout, HangoutConfig


@fixture
def hangout() -> Hangout:
    """Provide demo application with default configuration."""
    config = HangoutConfig()
    return Hangout(config=config)


@mark.asyncio
async def test_reception(hangout):
    """Test the reception method."""
    assert await hangout.reception() == "Hello, anonymous user!"
    assert await hangout.reception("John") == "Hello, John!"


@mark.asyncio
async def test_lobby(hangout):
    """Test the lobby method."""
    assert await hangout.lobby("John") == "Hello, John!"


@mark.asyncio
async def test_lounge(hangout):
    """Test the lounge method."""
    assert await hangout.lounge("John") == "Hello, dear John, have a beer!"
