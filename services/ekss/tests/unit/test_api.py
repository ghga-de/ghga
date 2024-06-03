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

"""Testing the basics of the service API"""

import pytest
from fastapi.testclient import TestClient

from ekss.adapters.inbound.fastapi_.main import setup_app
from ekss.config import CONFIG

app = setup_app(CONFIG)
client = TestClient(app=app)


@pytest.mark.asyncio
async def test_health_check():
    """Test that the health check endpoint works."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "OK"}
