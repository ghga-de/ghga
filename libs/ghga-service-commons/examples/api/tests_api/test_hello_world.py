# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Test the hello world app."""

import pytest
from hello_world_web_server.__main__ import app

from ghga_service_commons.api.testing import AsyncTestClient

client = AsyncTestClient(app)


@pytest.mark.asyncio
async def test_hello_world():
    """Test that the hello world app works as expected."""
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json() == "Hello World."
