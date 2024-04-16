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

"""Test the correlation ID middleware."""

import pytest
from fastapi import FastAPI

from ghga_service_commons.api.api import (
    CORRELATION_ID_HEADER_NAME,
    ApiConfigBase,
    configure_app,
)
from ghga_service_commons.api.testing import AsyncTestClient

VALID_CORRELATION_ID = "5deb0e61-5058-4e96-92d4-0529d045832e"


@pytest.mark.parametrize(
    "preset_id,generate_correlation_id,status_code",
    [
        (VALID_CORRELATION_ID, False, 200),  # happy path
        (VALID_CORRELATION_ID, True, 200),  # also fine
        ("invalid", False, 400),  # error for bad cid header
        ("invalid", True, 400),  # the generate flag is irrelevant
        ("", False, 400),  # No error for empty string cid header
        ("", True, 200),  # empty string with generate flag is fine
    ],
)
@pytest.mark.asyncio
async def test_middleware(
    preset_id: str,
    generate_correlation_id: bool,
    status_code: int,
):
    """Test that the InvalidCorrelationIdErrors are returned as 400 status-code responses."""
    app = FastAPI()

    config = ApiConfigBase(generate_correlation_id=generate_correlation_id)
    configure_app(app, config)

    # dummy endpoint to get a 200 status code
    app.get("/")(lambda: "some response")

    async with AsyncTestClient(app=app) as rest_client:
        response = await rest_client.get(
            "/", headers={CORRELATION_ID_HEADER_NAME: preset_id}
        )

        assert response.status_code == status_code
