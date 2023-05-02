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

"""Testing the testing module."""

import pytest
from fastapi import FastAPI

from ghga_service_commons.api.testing import AsyncTestClient


@pytest.mark.asyncio
async def test_async_test_client():
    """Test the AsyncTestClient."""

    app = FastAPI()

    @app.get("/")
    def index():
        return "Hello World"

    async with AsyncTestClient(app) as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert response.json() == "Hello World"
