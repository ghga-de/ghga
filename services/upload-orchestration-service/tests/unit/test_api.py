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
"""Tests that check the REST API's behavior and auth handling"""

from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from ghga_event_schemas.pydantic_ import (
    FileUpload,
    FileUploadState,
    ResearchDataUploadBox,
)
from ghga_service_commons.api.testing import AsyncTestClient
from ghga_service_commons.utils.jwt_helpers import sign_and_serialize_token
from hexkit.utils import now_utc_ms_prec

from tests.fixtures import ConfigFixture
from uos.core.models import BoxRetrievalResults, GrantWithBoxInfo
from uos.inject import prepare_rest_app
from uos.ports.inbound.orchestrator import UploadOrchestratorPort
from uos.ports.outbound.http import FileBoxClientPort

pytestmark = pytest.mark.asyncio()
TEST_DS_ID = UUID("f698158d-8417-4368-bb45-349277bc45ee")
TEST_BOX_ID = UUID("bf344cd4-0c1b-434a-93d1-36a11b6b02d9")
INVALID_HEADER: dict[str, str] = {"Authorization": "Bearer ab12"}

DS_AUTH_CLAIMS = {
    "name": "John Doe",
    "email": "john@home.org",
    "title": "Dr.",
    "id": str(TEST_DS_ID),
    "roles": ["data_steward"],
}
USER_AUTH_CLAIMS = DS_AUTH_CLAIMS.copy()
del USER_AUTH_CLAIMS["roles"]


def headers_for_token(token: str) -> dict[str, str]:
    """Get the Authorization headers for the given token."""
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(name="user_auth_headers")
def fixture_user_auth_headers(config: ConfigFixture) -> dict[str, str]:
    """Get auth headers for testing"""
    token = sign_and_serialize_token(USER_AUTH_CLAIMS, config.jwk)
    return headers_for_token(token)


@pytest.fixture(name="ds_auth_headers")
def fixture_ds_auth_headers(config: ConfigFixture) -> dict[str, str]:
    """Get auth headers for testing"""
    token = sign_and_serialize_token(DS_AUTH_CLAIMS, config.jwk)
    return headers_for_token(token)


@pytest.fixture(name="bad_auth_headers")
def fixture_bad_auth_headers(config: ConfigFixture) -> dict[str, str]:
    """Get a invalid auth headers for testing"""
    claims = DS_AUTH_CLAIMS.copy()
    del claims["id"]
    token = sign_and_serialize_token(claims, config.jwk)
    return headers_for_token(token)


async def test_health(config: ConfigFixture):
    """Test the health endpoint returns a 200"""
    async with (
        prepare_rest_app(
            config=config.config, upload_orchestrator_override=AsyncMock()
        ) as app,
        AsyncTestClient(app=app) as rest_client,
    ):
        response = await rest_client.get("/health")
        assert response.status_code == 200


async def test_get_research_data_upload_box(
    config: ConfigFixture, user_auth_headers, bad_auth_headers
):
    """Test the GET /boxes/{box_id} endpoint."""
    orchestrator = AsyncMock()
    async with (
        prepare_rest_app(
            config=config.config, upload_orchestrator_override=orchestrator
        ) as app,
        AsyncTestClient(app=app) as rest_client,
    ):
        # unauthenticated
        url = f"/boxes/{TEST_BOX_ID}"
        response = await rest_client.get(url)
        assert response.status_code == 403

        # bad credentials
        response = await rest_client.get(url, headers=bad_auth_headers)
        assert response.status_code == 401

        # normal response (patch mock)
        box = ResearchDataUploadBox(
            state="open",
            title="test",
            description="desc",
            last_changed=now_utc_ms_prec(),
            changed_by=TEST_DS_ID,
            id=TEST_BOX_ID,
            file_upload_box_id=uuid4(),
            storage_alias="HD",
        )
        orchestrator.get_research_data_upload_box.return_value = box
        response = await rest_client.get(url, headers=user_auth_headers)
        assert response.status_code == 200
        assert response.json() == box.model_dump(mode="json")

        # handle box access error from core -- we obscure this with 404 for security
        orchestrator.reset_mock()
        orchestrator.get_research_data_upload_box.side_effect = (
            UploadOrchestratorPort.BoxAccessError()
        )
        response = await rest_client.get(url, headers=user_auth_headers)
        assert response.status_code == 404

        # handle box not found error from core
        orchestrator.reset_mock()
        orchestrator.get_research_data_upload_box.side_effect = (
            UploadOrchestratorPort.BoxNotFoundError(box_id=box.id)
        )
        response = await rest_client.get(url, headers=user_auth_headers)
        assert response.status_code == 404

        # handle other exception
        orchestrator.reset_mock()
        orchestrator.get_research_data_upload_box.side_effect = TypeError()
        response = await rest_client.get(url, headers=user_auth_headers)
        assert response.status_code == 500


async def test_create_research_data_upload_box(
    config: ConfigFixture, ds_auth_headers, user_auth_headers, bad_auth_headers
):
    """Test the POST /boxes endpoint"""
    orchestrator = AsyncMock()
    async with (
        prepare_rest_app(
            config=config.config, upload_orchestrator_override=orchestrator
        ) as app,
        AsyncTestClient(app=app) as rest_client,
    ):
        url = "/boxes"
        request_data = {
            "title": "Test Box",
            "description": "Test description",
            "storage_alias": "HD01",
        }

        # unauthenticated
        response = await rest_client.post(url, json=request_data)
        assert response.status_code == 403

        # bad credentials
        response = await rest_client.post(
            url, json=request_data, headers=bad_auth_headers
        )
        assert response.status_code == 401

        # normal response but user is not a data steward (no data_steward role)
        response = await rest_client.post(
            url, json=request_data, headers=user_auth_headers
        )
        assert response.status_code == 403

        # normal response with data steward role
        # Mock the orchestrator to return a box ID
        test_box_id = uuid4()
        orchestrator.create_research_data_upload_box.return_value = test_box_id
        response = await rest_client.post(
            url, json=request_data, headers=ds_auth_headers
        )
        assert response.status_code == 201
        assert response.json() == str(test_box_id)

        # handle file box service error from core
        orchestrator.reset_mock()
        orchestrator.create_research_data_upload_box.side_effect = (
            FileBoxClientPort.OperationError()
        )
        response = await rest_client.post(
            url, json=request_data, headers=ds_auth_headers
        )
        assert response.status_code == 500

        # handle other exception
        orchestrator.reset_mock()
        orchestrator.create_research_data_upload_box.side_effect = TypeError()
        response = await rest_client.post(
            url, json=request_data, headers=ds_auth_headers
        )
        assert response.status_code == 500


async def test_update_research_data_upload_box(
    config: ConfigFixture, ds_auth_headers, user_auth_headers, bad_auth_headers
):
    """Test the PATCH /boxes/{box_id} endpoint."""
    orchestrator = AsyncMock()
    async with (
        prepare_rest_app(
            config=config.config, upload_orchestrator_override=orchestrator
        ) as app,
        AsyncTestClient(app=app) as rest_client,
    ):
        url = f"/boxes/{TEST_BOX_ID}"
        request_data = {"title": "Updated Title", "description": "Updated description"}

        # unauthenticated
        response = await rest_client.patch(url, json=request_data)
        assert response.status_code == 403

        # bad credentials
        response = await rest_client.patch(
            url, json=request_data, headers=bad_auth_headers
        )
        assert response.status_code == 401

        # normal response with user auth (should work for regular users too)
        orchestrator.update_research_data_upload_box.return_value = None
        response = await rest_client.patch(
            url, json=request_data, headers=user_auth_headers
        )
        assert response.status_code == 204

        # normal response with data steward auth
        orchestrator.reset_mock()
        orchestrator.update_research_data_upload_box.return_value = None
        response = await rest_client.patch(
            url, json=request_data, headers=ds_auth_headers
        )
        assert response.status_code == 204

        # handle box access error from core
        orchestrator.reset_mock()
        orchestrator.update_research_data_upload_box.side_effect = (
            UploadOrchestratorPort.BoxAccessError()
        )
        response = await rest_client.patch(
            url, json=request_data, headers=user_auth_headers
        )
        assert response.status_code == 403

        # handle box not found error from core
        orchestrator.reset_mock()
        orchestrator.update_research_data_upload_box.side_effect = (
            UploadOrchestratorPort.BoxNotFoundError(box_id=TEST_BOX_ID)
        )
        response = await rest_client.patch(
            url, json=request_data, headers=user_auth_headers
        )
        assert response.status_code == 404

        # handle file box service error from core
        orchestrator.reset_mock()
        orchestrator.update_research_data_upload_box.side_effect = (
            FileBoxClientPort.OperationError()
        )
        response = await rest_client.patch(
            url, json=request_data, headers=user_auth_headers
        )
        assert response.status_code == 500

        # handle other exception
        orchestrator.reset_mock()
        orchestrator.update_research_data_upload_box.side_effect = TypeError()
        response = await rest_client.patch(
            url, json=request_data, headers=user_auth_headers
        )
        assert response.status_code == 500


async def test_grant_upload_access(
    config: ConfigFixture, ds_auth_headers, user_auth_headers, bad_auth_headers
):
    """Test the POST /access-grants endpoint"""
    orchestrator = AsyncMock()
    async with (
        prepare_rest_app(
            config=config.config, upload_orchestrator_override=orchestrator
        ) as app,
        AsyncTestClient(app=app) as rest_client,
    ):
        url = "/access-grants"
        request_data = {
            "user_id": str(uuid4()),
            "iva_id": str(uuid4()),
            "box_id": str(TEST_BOX_ID),
            "valid_from": now_utc_ms_prec().isoformat(),
            "valid_until": (now_utc_ms_prec() + timedelta(minutes=180)).isoformat(),
        }

        # unauthenticated
        response = await rest_client.post(url, json=request_data)
        assert response.status_code == 403

        # bad credentials
        response = await rest_client.post(
            url, json=request_data, headers=bad_auth_headers
        )
        assert response.status_code == 401

        # normal response but user is not a data steward (no data_steward role)
        response = await rest_client.post(
            url, json=request_data, headers=user_auth_headers
        )
        assert response.status_code == 403

        # normal response with data steward role
        orchestrator.grant_upload_access.return_value = None
        response = await rest_client.post(
            url, json=request_data, headers=ds_auth_headers
        )
        assert response.status_code == 201
        assert response.json() == {"message": "Upload access granted successfully"}

        # handle other exception
        orchestrator.reset_mock()
        orchestrator.grant_upload_access.side_effect = TypeError()
        response = await rest_client.post(
            url, json=request_data, headers=ds_auth_headers
        )
        assert response.status_code == 500


async def test_list_upload_box_files(
    config: ConfigFixture, ds_auth_headers, user_auth_headers, bad_auth_headers
):
    """Test the GET /boxes/{box_id}/uploads endpoint."""
    orchestrator = AsyncMock()
    async with (
        prepare_rest_app(
            config=config.config, upload_orchestrator_override=orchestrator
        ) as app,
        AsyncTestClient(app=app) as rest_client,
    ):
        url = f"/boxes/{TEST_BOX_ID}/uploads"

        # unauthenticated
        response = await rest_client.get(url)
        assert response.status_code == 403

        # bad credentials
        response = await rest_client.get(url, headers=bad_auth_headers)
        assert response.status_code == 401

        # normal response with user auth
        file_list = [
            FileUpload(
                id=uuid4(),
                box_id=TEST_BOX_ID,
                alias=f"test{i}",
                checksum=f"checksum{i}",
                size=1000 + i * 100,
                state=FileUploadState.ARCHIVED,
                completed=True,
            )
            for i in range(3)
        ]

        file_list_json = [file.model_dump(mode="json") for file in file_list]
        orchestrator.get_upload_box_files.return_value = file_list
        response = await rest_client.get(url, headers=user_auth_headers)
        assert response.status_code == 200
        assert response.json() == file_list_json

        # normal response with data steward auth
        response = await rest_client.get(url, headers=ds_auth_headers)
        assert response.status_code == 200
        assert response.json() == file_list_json

        # handle box access error from core
        orchestrator.reset_mock()
        orchestrator.get_upload_box_files.side_effect = (
            UploadOrchestratorPort.BoxAccessError()
        )
        response = await rest_client.get(url, headers=user_auth_headers)
        assert response.status_code == 403

        # handle box not found error from core
        orchestrator.reset_mock()
        orchestrator.get_upload_box_files.side_effect = (
            UploadOrchestratorPort.BoxNotFoundError(box_id=TEST_BOX_ID)
        )
        response = await rest_client.get(url, headers=user_auth_headers)
        assert response.status_code == 404

        # handle other exception (including FileBoxClient errors that bubble up)
        orchestrator.reset_mock()
        orchestrator.get_upload_box_files.side_effect = TypeError()
        response = await rest_client.get(url, headers=user_auth_headers)
        assert response.status_code == 500


async def test_revoke_upload_access_grant(
    config: ConfigFixture, ds_auth_headers, user_auth_headers, bad_auth_headers
):
    """Test the DELETE /access-grants/{grant_id} endpoint"""
    orchestrator = AsyncMock()
    test_grant_id = uuid4()

    async with (
        prepare_rest_app(
            config=config.config, upload_orchestrator_override=orchestrator
        ) as app,
        AsyncTestClient(app=app) as rest_client,
    ):
        url = f"/access-grants/{test_grant_id}"

        # unauthenticated
        response = await rest_client.delete(url)
        assert response.status_code == 403

        # bad credentials
        response = await rest_client.delete(url, headers=bad_auth_headers)
        assert response.status_code == 401

        # normal response but user is not a data steward (no data_steward role)
        response = await rest_client.delete(url, headers=user_auth_headers)
        assert response.status_code == 403

        # normal response with data steward role
        orchestrator.revoke_upload_access_grant.return_value = None
        response = await rest_client.delete(url, headers=ds_auth_headers)
        assert response.status_code == 204

        # handle grant not found error from core
        orchestrator.reset_mock()
        orchestrator.revoke_upload_access_grant.side_effect = (
            UploadOrchestratorPort.GrantNotFoundError(grant_id=test_grant_id)
        )
        response = await rest_client.delete(url, headers=ds_auth_headers)
        assert response.status_code == 404

        # handle other exception
        orchestrator.reset_mock()
        orchestrator.revoke_upload_access_grant.side_effect = TypeError()
        response = await rest_client.delete(url, headers=ds_auth_headers)
        assert response.status_code == 500


async def test_get_upload_access_grants(
    config: ConfigFixture, ds_auth_headers, user_auth_headers, bad_auth_headers
):
    """Test the GET /access-grants endpoint"""
    orchestrator = AsyncMock()
    async with (
        prepare_rest_app(
            config=config.config, upload_orchestrator_override=orchestrator
        ) as app,
        AsyncTestClient(app=app) as rest_client,
    ):
        url = "/access-grants"

        # unauthenticated
        response = await rest_client.get(url)
        assert response.status_code == 403

        # bad credentials
        response = await rest_client.get(url, headers=bad_auth_headers)
        assert response.status_code == 401

        # normal response but user is not a data steward (no data_steward role)
        response = await rest_client.get(url, headers=user_auth_headers)
        assert response.status_code == 403

        test_grants = [
            GrantWithBoxInfo(
                id=uuid4(),
                user_id=uuid4(),
                iva_id=uuid4(),
                box_id=TEST_BOX_ID,
                created=now_utc_ms_prec(),
                valid_from=now_utc_ms_prec(),
                valid_until=now_utc_ms_prec() + timedelta(days=7),
                user_name="Test User",
                user_email="test@example.com",
                user_title="Dr.",
                box_title="Test Box",
                box_description="Test box description",
            )
        ]
        orchestrator.get_upload_access_grants.return_value = test_grants
        response = await rest_client.get(url, headers=ds_auth_headers)
        assert response.status_code == 200
        assert response.json() == [
            grant.model_dump(mode="json") for grant in test_grants
        ]

        # test with query parameters
        response = await rest_client.get(
            url,
            headers=ds_auth_headers,
            params={"user_id": str(uuid4()), "valid": "true"},
        )
        assert response.status_code == 200

        # handle other exception
        orchestrator.reset_mock()
        orchestrator.get_upload_access_grants.side_effect = TypeError()
        response = await rest_client.get(url, headers=ds_auth_headers)
        assert response.status_code == 500


async def test_get_boxes(
    config: ConfigFixture,
    ds_auth_headers: dict[str, str],
    user_auth_headers: dict[str, str],
):
    """Test GET /boxes endpoint."""
    orchestrator = AsyncMock(spec=UploadOrchestratorPort)

    # Create test boxes
    test_boxes = [
        ResearchDataUploadBox(
            id=uuid4(),
            state="open",
            title="Box A",
            description="Description A",
            last_changed=now_utc_ms_prec(),
            changed_by=TEST_DS_ID,
            file_upload_box_id=uuid4(),
            storage_alias="HD01",
        ),
        ResearchDataUploadBox(
            id=uuid4(),
            state="open",
            title="Box B",
            description="Description B",
            last_changed=now_utc_ms_prec(),
            changed_by=TEST_DS_ID,
            file_upload_box_id=uuid4(),
            storage_alias="HD01",
        ),
    ]

    async with (
        prepare_rest_app(
            config=config.config, upload_orchestrator_override=orchestrator
        ) as app,
        AsyncTestClient(app=app) as rest_client,
    ):
        url = "/boxes"

        # Test successful data steward request
        orchestrator.get_research_data_upload_boxes.return_value = BoxRetrievalResults(
            count=2, boxes=test_boxes
        )
        response = await rest_client.get(url, headers=ds_auth_headers)
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["count"] == 2
        assert len(response_data["boxes"]) == 2
        assert response_data["boxes"][0]["title"] == "Box A"
        assert response_data["boxes"][1]["title"] == "Box B"

        # Test with non-data steward (regular user)
        orchestrator.reset_mock()
        orchestrator.get_research_data_upload_boxes.return_value = BoxRetrievalResults(
            count=1, boxes=[test_boxes[0]]
        )
        response = await rest_client.get(url, headers=user_auth_headers)
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["count"] == 1
        assert len(response_data["boxes"]) == 1

        # Test locked parameter filtering
        orchestrator.reset_mock()
        locked_box = test_boxes[0].model_copy(update={"locked": True})
        orchestrator.get_research_data_upload_boxes.return_value = BoxRetrievalResults(
            count=1, boxes=[locked_box]
        )
        response = await rest_client.get(
            url, headers=ds_auth_headers, params={"locked": "true"}
        )
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["count"] == 1
        assert len(response_data["boxes"]) == 1

        # Verify orchestrator was called with locked=True
        call_args = orchestrator.get_research_data_upload_boxes.call_args
        assert call_args.kwargs["locked"] is True

        # Test locked=false parameter
        orchestrator.reset_mock()
        unlocked_box = test_boxes[1].model_copy(update={"locked": False})
        orchestrator.get_research_data_upload_boxes.return_value = BoxRetrievalResults(
            count=1, boxes=[unlocked_box]
        )
        response = await rest_client.get(
            url, headers=ds_auth_headers, params={"locked": "false"}
        )
        assert response.status_code == 200
        call_args = orchestrator.get_research_data_upload_boxes.call_args
        assert call_args.kwargs["locked"] is False

        # Test other exception
        orchestrator.reset_mock()
        orchestrator.get_research_data_upload_boxes.side_effect = ValueError(
            "Test error"
        )
        response = await rest_client.get(url, headers=ds_auth_headers)
        assert response.status_code == 500


@pytest.mark.parametrize(
    "params",
    [
        {"skip": -1},
        {"skip": "abc"},
        {"limit": -1},
        {"limit": "abc"},
    ],
)
async def test_get_boxes_bad_parameters(config: ConfigFixture, ds_auth_headers, params):
    """Test the GET /boxes endpoint with bad parameters but valid auth context"""
    orchestrator = AsyncMock(spec=UploadOrchestratorPort)
    async with (
        prepare_rest_app(
            config=config.config, upload_orchestrator_override=orchestrator
        ) as app,
        AsyncTestClient(app=app) as rest_client,
    ):
        url = "/boxes"
        response = await rest_client.get(url, headers=ds_auth_headers, params=params)
        assert response.status_code == 422
