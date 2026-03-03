# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
"""Unit tests for the AccessionClient"""

import json
from datetime import timedelta
from typing import Literal, cast
from uuid import UUID, uuid4

import httpx
import pytest
from ghga_service_commons.auth.jwt_auth import JWTAuthConfig, JWTAuthContextProvider
from ghga_service_commons.utils.utc_dates import UTCDatetime
from hexkit.utils import now_utc_ms_prec
from pydantic import UUID4, BaseModel
from pytest_httpx import HTTPXMock

from tests.fixtures import ConfigFixture
from uos.adapters.outbound.http import AccessionClient
from uos.core.models import AccessionMap

pytestmark = pytest.mark.asyncio

TEST_BOX_ID = UUID("a1b2c3d4-e5f6-4890-abcd-ef1234567890")
TEST_STUDY_PID = "GHGA-STUDY-001"

ACCESSION_MAP = AccessionMap(
    box_id=TEST_BOX_ID,
    mapping={"GHGA:file1": uuid4(), "GHGA:file2": uuid4()},
)


class WOTClaimsModel(BaseModel):
    """Model which defines the expected WOT format for accession map submission"""

    work_type: Literal["map"]
    user_id: UUID4
    study_pid: str
    iat: UTCDatetime
    exp: UTCDatetime


async def test_submission(
    config: ConfigFixture, httpx_mock: HTTPXMock, httpx_client: httpx.AsyncClient
):
    """Test that the AccessionClient sends a request to the right URL with the right
    payload given an AccessionMap.
    """
    accession_client = AccessionClient(config=config.config, httpx_client=httpx_client)
    test_user_id = uuid4()

    httpx_mock.add_response(204)
    await accession_client.submit_accession_map(
        accession_map=ACCESSION_MAP, study_pid=TEST_STUDY_PID, user_id=test_user_id
    )

    # Check off-normal status code
    httpx_mock.add_response(500, json={"error": "Some error occurred."})
    with pytest.raises(AccessionClient.OperationError):
        await accession_client.submit_accession_map(
            accession_map=ACCESSION_MAP, study_pid=TEST_STUDY_PID, user_id=test_user_id
        )


async def test_wot_formation(
    config: ConfigFixture, httpx_mock: HTTPXMock, httpx_client: httpx.AsyncClient
):
    """Test that the AccessionClient sends a properly formed work order token and
    includes study_pid in the request body.
    """
    auth_config = JWTAuthConfig(
        auth_key=config.signing_jwk.export_public(),
        auth_check_claims=dict.fromkeys(
            ["work_type", "user_id", "study_pid", "iat", "exp"]
        ),
    )
    auth_context_provider = JWTAuthContextProvider(
        config=auth_config, context_class=WOTClaimsModel
    )
    test_user_id = uuid4()

    async def callback(request: httpx.Request):
        token = cast(str, request.headers.get("Authorization"))
        token = token.removeprefix("Bearer ")
        context = await auth_context_provider.get_context(token)
        assert context
        assert context.work_type == "map"
        assert context.user_id == test_user_id
        assert context.study_pid == TEST_STUDY_PID
        assert context.iat - now_utc_ms_prec() < timedelta(seconds=3)
        body = json.loads(request.content)
        assert body["study_pid"] == TEST_STUDY_PID
        return httpx.Response(204)

    httpx_mock.add_callback(callback=callback)
    accession_client = AccessionClient(config=config.config, httpx_client=httpx_client)
    await accession_client.submit_accession_map(
        accession_map=ACCESSION_MAP, study_pid=TEST_STUDY_PID, user_id=test_user_id
    )
