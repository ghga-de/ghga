# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Test context utils."""

import sys
from contextlib import nullcontext

import pytest

from ghga_service_commons.utils.context import asyncnullcontext


@pytest.mark.asyncio
async def test_asyncnullcontext():
    """Test the asyncnullcontext context manager."""
    value = "test"

    modern_python = sys.version_info >= (3, 10)

    try:
        async with nullcontext(value) as test:
            assert test == value
    except AttributeError:
        assert not modern_python, "nullcontext should work with async"

    async with asyncnullcontext(value) as test:
        assert test == value
