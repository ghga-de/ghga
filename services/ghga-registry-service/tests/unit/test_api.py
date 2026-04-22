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
"""Tests that check the REST API's behavior and auth handling"""

from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from ghga_service_commons.api.testing import AsyncTestClient
from hexkit.utils import now_utc_ms_prec

from rs.config import Config
from rs.core.models import (
    BoxRetrievalResults,
    FileUploadWithAccession,
    GrantId,
    GrantWithBoxInfo,
    ResearchDataUploadBox,
)
from rs.inject import prepare_rest_app
from rs.ports.inbound.rdub_manager import RDUBManagerPort
from rs.ports.outbound.http import FileBoxClientPort
from tests.fixtures.utils import TEST_BOX_ID, TEST_DS_ID

pytestmark = pytest.mark.asyncio


async def test_health(config: Config):
    """Test the health endpoint returns a 200"""
    async with (
        prepare_rest_app(config=config, ghga_registry_override=AsyncMock()) as app,
        AsyncTestClient(app=app) as rest_client,
    ):
        response = await rest_client.get("/health")
        assert response.status_code == 200


async def test_get_research_data_upload_box(
    config: Config, user_auth_headers, bad_auth_headers
):
    """Test the GET /upload-boxes/{box_id} endpoint."""
    ghga_registry = AsyncMock()
    async with (
        prepare_rest_app(config=config, ghga_registry_override=ghga_registry) as app,
        AsyncTestClient(app=app) as rest_client,
    ):
        # unauthenticated
        url = f"/upload-boxes/{TEST_BOX_ID}"
        response = await rest_client.get(url)
        assert response.status_code == 401

        # bad credentials
        response = await rest_client.get(url, headers=bad_auth_headers)
        assert response.status_code == 401

        # normal response (patch mock)
        box = ResearchDataUploadBox(
            version=0,
            state="open",
            title="test",
            description="desc",
            last_changed=now_utc_ms_prec(),
            changed_by=TEST_DS_ID,
            id=TEST_BOX_ID,
            file_upload_box_id=uuid4(),
            file_upload_box_version=0,
            file_upload_box_state="open",
            storage_alias="HD",
        )
        ghga_registry.rdub_manager.get_research_data_upload_box.return_value = box
        response = await rest_client.get(url, headers=user_auth_headers)
        assert response.status_code == 200
        assert response.json() == box.model_dump(mode="json")

        # handle box access error from core -- we obscure this with 404 for security
        ghga_registry.reset_mock()
        ghga_registry.rdub_manager.get_research_data_upload_box.side_effect = (
            RDUBManagerPort.BoxAccessError()
        )
        response = await rest_client.get(url, headers=user_auth_headers)
        assert response.status_code == 404

        # handle box not found error from core
        ghga_registry.reset_mock()
        ghga_registry.rdub_manager.get_research_data_upload_box.side_effect = (
            RDUBManagerPort.BoxNotFoundError(box_id=box.id)
        )
        response = await rest_client.get(url, headers=user_auth_headers)
        assert response.status_code == 404

        # handle other exception
        ghga_registry.reset_mock()
        ghga_registry.rdub_manager.get_research_data_upload_box.side_effect = (
            TypeError()
        )
        response = await rest_client.get(url, headers=user_auth_headers)
        assert response.status_code == 500


async def test_create_research_data_upload_box(
    config: Config, ds_auth_headers, user_auth_headers, bad_auth_headers
):
    """Test the POST /upload-boxes endpoint"""
    ghga_registry = AsyncMock()
    async with (
        prepare_rest_app(config=config, ghga_registry_override=ghga_registry) as app,
        AsyncTestClient(app=app) as rest_client,
    ):
        url = "/upload-boxes"
        request_data = {
            "title": "Test Box",
            "description": "Test description",
            "storage_alias": "HD01",
        }

        # unauthenticated
        response = await rest_client.post(url, json=request_data)
        assert response.status_code == 401

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
        # Mock the rdub_manager to return a box ID
        test_box_id = uuid4()
        ghga_registry.rdub_manager.create_research_data_upload_box.return_value = (
            test_box_id
        )
        response = await rest_client.post(
            url, json=request_data, headers=ds_auth_headers
        )
        assert response.status_code == 201
        assert response.json() == str(test_box_id)

        # handle file box service error from core
        ghga_registry.reset_mock()
        ghga_registry.rdub_manager.create_research_data_upload_box.side_effect = (
            FileBoxClientPort.OperationError()
        )
        response = await rest_client.post(
            url, json=request_data, headers=ds_auth_headers
        )
        assert response.status_code == 500

        # handle other exception
        ghga_registry.reset_mock()
        ghga_registry.rdub_manager.create_research_data_upload_box.side_effect = (
            TypeError()
        )
        response = await rest_client.post(
            url, json=request_data, headers=ds_auth_headers
        )
        assert response.status_code == 500


async def test_update_research_data_upload_box(
    config: Config, ds_auth_headers, user_auth_headers, bad_auth_headers
):
    """Test the PATCH /upload-boxes/{box_id} endpoint."""
    rdub_manager = AsyncMock()
    async with (
        prepare_rest_app(config=config, ghga_registry_override=rdub_manager) as app,
        AsyncTestClient(app=app) as rest_client,
    ):
        url = f"/upload-boxes/{TEST_BOX_ID}"
        request_data = {
            "version": 0,
            "title": "Updated Title",
            "description": "Updated description",
        }

        # unauthenticated
        response = await rest_client.patch(url, json=request_data)
        assert response.status_code == 401

        # bad credentials
        response = await rest_client.patch(
            url, json=request_data, headers=bad_auth_headers
        )
        assert response.status_code == 401

        # normal response with user auth (should work for regular users too)
        rdub_manager.rdub_manager.update_research_data_upload_box.return_value = None
        response = await rest_client.patch(
            url, json=request_data, headers=user_auth_headers
        )
        assert response.status_code == 204

        # normal response with data steward auth
        rdub_manager.reset_mock()
        rdub_manager.rdub_manager.update_research_data_upload_box.return_value = None
        response = await rest_client.patch(
            url, json=request_data, headers=ds_auth_headers
        )
        assert response.status_code == 204

        # handle box access error from core
        rdub_manager.reset_mock()
        rdub_manager.rdub_manager.update_research_data_upload_box.side_effect = (
            RDUBManagerPort.BoxAccessError()
        )
        response = await rest_client.patch(
            url, json=request_data, headers=user_auth_headers
        )
        assert response.status_code == 403

        # handle box not found error from core
        rdub_manager.reset_mock()
        rdub_manager.rdub_manager.update_research_data_upload_box.side_effect = (
            RDUBManagerPort.BoxNotFoundError(box_id=TEST_BOX_ID)
        )
        response = await rest_client.patch(
            url, json=request_data, headers=user_auth_headers
        )
        assert response.status_code == 404

        # handle version error from core
        rdub_manager.reset_mock()
        rdub_manager.rdub_manager.update_research_data_upload_box.side_effect = (
            RDUBManagerPort.VersionError()
        )
        response = await rest_client.patch(
            url, json=request_data, headers=user_auth_headers
        )
        assert response.status_code == 409

        # handle state change error from core
        rdub_manager.reset_mock()
        rdub_manager.rdub_manager.update_research_data_upload_box.side_effect = (
            RDUBManagerPort.StateChangeError(old_state="archived", new_state="open")
        )
        response = await rest_client.patch(
            url, json=request_data, headers=user_auth_headers
        )
        assert response.status_code == 409

        # handle file box service error from core
        rdub_manager.reset_mock()
        rdub_manager.rdub_manager.update_research_data_upload_box.side_effect = (
            FileBoxClientPort.OperationError()
        )
        response = await rest_client.patch(
            url, json=request_data, headers=user_auth_headers
        )
        assert response.status_code == 500

        # handle other exception
        rdub_manager.reset_mock()
        rdub_manager.rdub_manager.update_research_data_upload_box.side_effect = (
            TypeError()
        )
        response = await rest_client.patch(
            url, json=request_data, headers=user_auth_headers
        )
        assert response.status_code == 500


async def test_grant_upload_access(
    config: Config, ds_auth_headers, user_auth_headers, bad_auth_headers
):
    """Test the POST /upload-grants endpoint"""
    rdub_manager = AsyncMock()
    async with (
        prepare_rest_app(config=config, ghga_registry_override=rdub_manager) as app,
        AsyncTestClient(app=app) as rest_client,
    ):
        url = "/upload-grants"
        request_data = {
            "user_id": str(uuid4()),
            "iva_id": str(uuid4()),
            "box_id": str(TEST_BOX_ID),
            "valid_from": now_utc_ms_prec().isoformat(),
            "valid_until": (now_utc_ms_prec() + timedelta(minutes=180)).isoformat(),
        }

        # unauthenticated
        response = await rest_client.post(url, json=request_data)
        assert response.status_code == 401

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
        test_grant_id = uuid4()
        rdub_manager.rdub_manager.grant_upload_access.return_value = GrantId(
            id=test_grant_id
        )
        response = await rest_client.post(
            url, json=request_data, headers=ds_auth_headers
        )
        assert response.status_code == 201
        assert response.json() == {"id": str(test_grant_id)}

        # handle other exception
        rdub_manager.reset_mock()
        rdub_manager.rdub_manager.grant_upload_access.side_effect = TypeError()
        response = await rest_client.post(
            url, json=request_data, headers=ds_auth_headers
        )
        assert response.status_code == 500


async def test_list_upload_box_files(
    config: Config, ds_auth_headers, user_auth_headers, bad_auth_headers
):
    """Test the GET /upload-boxes/{box_id}/uploads endpoint."""
    rdub_manager = AsyncMock()
    async with (
        prepare_rest_app(config=config, ghga_registry_override=rdub_manager) as app,
        AsyncTestClient(app=app) as rest_client,
    ):
        url = f"/upload-boxes/{TEST_BOX_ID}/uploads"

        # unauthenticated
        response = await rest_client.get(url)
        assert response.status_code == 401

        # bad credentials
        response = await rest_client.get(url, headers=bad_auth_headers)
        assert response.status_code == 401

        # normal response with user auth
        file_list = [
            FileUploadWithAccession(
                id=uuid4(),
                box_id=TEST_BOX_ID,
                storage_alias="HD01",
                bucket_id="inbox",
                object_id=uuid4(),
                alias=f"test{i}",
                decrypted_sha256=f"checksum{i}",
                decrypted_size=1000 + i * 100,
                encrypted_size=1100 + i * 100,
                part_size=100,
                state="archived",
                state_updated=now_utc_ms_prec(),
            )
            for i in range(3)
        ]

        file_list_json = [file.model_dump(mode="json") for file in file_list]
        rdub_manager.rdub_manager.get_upload_box_files.return_value = file_list
        response = await rest_client.get(url, headers=user_auth_headers)
        assert response.status_code == 200
        assert response.json() == file_list_json

        # normal response with data steward auth
        response = await rest_client.get(url, headers=ds_auth_headers)
        assert response.status_code == 200
        assert response.json() == file_list_json

        # handle box access error from core
        rdub_manager.reset_mock()
        rdub_manager.rdub_manager.get_upload_box_files.side_effect = (
            RDUBManagerPort.BoxAccessError()
        )
        response = await rest_client.get(url, headers=user_auth_headers)
        assert response.status_code == 403

        # handle box not found error from core
        rdub_manager.reset_mock()
        rdub_manager.rdub_manager.get_upload_box_files.side_effect = (
            RDUBManagerPort.BoxNotFoundError(box_id=TEST_BOX_ID)
        )
        response = await rest_client.get(url, headers=user_auth_headers)
        assert response.status_code == 404

        # handle other exception (including FileBoxClient errors that bubble up)
        rdub_manager.reset_mock()
        rdub_manager.rdub_manager.get_upload_box_files.side_effect = TypeError()
        response = await rest_client.get(url, headers=user_auth_headers)
        assert response.status_code == 500


async def test_revoke_upload_access_grant(
    config: Config, ds_auth_headers, user_auth_headers, bad_auth_headers
):
    """Test the DELETE /upload-grants/{grant_id} endpoint"""
    rdub_manager = AsyncMock()
    test_grant_id = uuid4()

    async with (
        prepare_rest_app(config=config, ghga_registry_override=rdub_manager) as app,
        AsyncTestClient(app=app) as rest_client,
    ):
        url = f"/upload-grants/{test_grant_id}"

        # unauthenticated
        response = await rest_client.delete(url)
        assert response.status_code == 401

        # bad credentials
        response = await rest_client.delete(url, headers=bad_auth_headers)
        assert response.status_code == 401

        # normal response but user is not a data steward (no data_steward role)
        response = await rest_client.delete(url, headers=user_auth_headers)
        assert response.status_code == 403

        # normal response with data steward role
        rdub_manager.rdub_manager.revoke_upload_access_grant.return_value = None
        response = await rest_client.delete(url, headers=ds_auth_headers)
        assert response.status_code == 204

        # handle grant not found error from core
        rdub_manager.reset_mock()
        rdub_manager.rdub_manager.revoke_upload_access_grant.side_effect = (
            RDUBManagerPort.GrantNotFoundError(grant_id=test_grant_id)
        )
        response = await rest_client.delete(url, headers=ds_auth_headers)
        assert response.status_code == 404

        # handle other exception
        rdub_manager.reset_mock()
        rdub_manager.rdub_manager.revoke_upload_access_grant.side_effect = TypeError()
        response = await rest_client.delete(url, headers=ds_auth_headers)
        assert response.status_code == 500


async def test_get_upload_access_grants(
    config: Config, ds_auth_headers, user_auth_headers, bad_auth_headers
):
    """Test the GET /upload-grants endpoint"""
    rdub_manager = AsyncMock()
    async with (
        prepare_rest_app(config=config, ghga_registry_override=rdub_manager) as app,
        AsyncTestClient(app=app) as rest_client,
    ):
        url = "/upload-grants"

        # unauthenticated
        response = await rest_client.get(url)
        assert response.status_code == 401

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
                box_state="open",
                box_version=0,
            )
        ]
        rdub_manager.rdub_manager.get_upload_access_grants.return_value = test_grants
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
        rdub_manager.reset_mock()
        rdub_manager.rdub_manager.get_upload_access_grants.side_effect = TypeError()
        response = await rest_client.get(url, headers=ds_auth_headers)
        assert response.status_code == 500


async def test_get_boxes(
    config: Config,
    ds_auth_headers: dict[str, str],
    user_auth_headers: dict[str, str],
):
    """Test GET /upload-boxes endpoint."""
    rdub_manager = AsyncMock()

    # Create test boxes
    test_boxes = [
        ResearchDataUploadBox(
            version=0,
            id=uuid4(),
            state="open",
            title="Box A",
            description="Description A",
            last_changed=now_utc_ms_prec(),
            changed_by=TEST_DS_ID,
            file_upload_box_id=uuid4(),
            file_upload_box_version=0,
            file_upload_box_state="open",
            storage_alias="HD01",
        ),
        ResearchDataUploadBox(
            version=0,
            id=uuid4(),
            state="open",
            title="Box B",
            description="Description B",
            last_changed=now_utc_ms_prec(),
            changed_by=TEST_DS_ID,
            file_upload_box_id=uuid4(),
            file_upload_box_version=0,
            file_upload_box_state="open",
            storage_alias="HD01",
        ),
    ]

    async with (
        prepare_rest_app(config=config, ghga_registry_override=rdub_manager) as app,
        AsyncTestClient(app=app) as rest_client,
    ):
        url = "/upload-boxes"

        # Test successful data steward request
        rdub_manager.rdub_manager.get_research_data_upload_boxes.return_value = (
            BoxRetrievalResults(count=2, boxes=test_boxes)
        )
        response = await rest_client.get(url, headers=ds_auth_headers)
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["count"] == 2
        assert len(response_data["boxes"]) == 2
        assert response_data["boxes"][0]["title"] == "Box A"
        assert response_data["boxes"][1]["title"] == "Box B"

        # Test with non-data steward (regular user)
        rdub_manager.reset_mock()
        rdub_manager.rdub_manager.get_research_data_upload_boxes.return_value = (
            BoxRetrievalResults(count=1, boxes=[test_boxes[0]])
        )
        response = await rest_client.get(url, headers=user_auth_headers)
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["count"] == 1
        assert len(response_data["boxes"]) == 1

        # Test locked parameter filtering
        rdub_manager.reset_mock()
        locked_box = test_boxes[0].model_copy(update={"locked": True})
        rdub_manager.rdub_manager.get_research_data_upload_boxes.return_value = (
            BoxRetrievalResults(count=1, boxes=[locked_box])
        )
        response = await rest_client.get(
            url, headers=ds_auth_headers, params={"state": "locked"}
        )
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["count"] == 1
        assert len(response_data["boxes"]) == 1

        # Verify rdub_manager was called with state="locked"
        call_args = rdub_manager.rdub_manager.get_research_data_upload_boxes.call_args
        assert call_args.kwargs["state"] == "locked"

        # Test locked=false parameter
        rdub_manager.reset_mock()
        unlocked_box = test_boxes[1].model_copy(update={"locked": False})
        rdub_manager.rdub_manager.get_research_data_upload_boxes.return_value = (
            BoxRetrievalResults(count=1, boxes=[unlocked_box])
        )
        response = await rest_client.get(
            url, headers=ds_auth_headers, params={"state": "open"}
        )
        assert response.status_code == 200
        call_args = rdub_manager.rdub_manager.get_research_data_upload_boxes.call_args
        assert call_args.kwargs["state"] == "open"

        # Test other exception
        rdub_manager.reset_mock()
        rdub_manager.rdub_manager.get_research_data_upload_boxes.side_effect = (
            ValueError("Test error")
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
async def test_get_boxes_bad_parameters(config: Config, ds_auth_headers, params):
    """Test the GET /upload-boxes endpoint with bad parameters but valid auth context"""
    rdub_manager = AsyncMock()
    async with (
        prepare_rest_app(config=config, ghga_registry_override=rdub_manager) as app,
        AsyncTestClient(app=app) as rest_client,
    ):
        url = "/upload-boxes"
        response = await rest_client.get(url, headers=ds_auth_headers, params=params)
        assert response.status_code == 422


async def test_archive_via_update_endpoint(
    config: Config, ds_auth_headers, user_auth_headers, bad_auth_headers
):
    """Test archiving a box through the PATCH /upload-boxes/{box_id} endpoint"""
    rdub_manager = AsyncMock()
    async with (
        prepare_rest_app(config=config, ghga_registry_override=rdub_manager) as app,
        AsyncTestClient(app=app) as rest_client,
    ):
        url = f"/upload-boxes/{TEST_BOX_ID}"
        request_data = {"version": 1, "state": "archived"}

        # unauthenticated
        response = await rest_client.patch(url, json=request_data)
        assert response.status_code == 401

        # bad credentials
        response = await rest_client.patch(
            url, json=request_data, headers=bad_auth_headers
        )
        assert response.status_code == 401

        # normal response but user is not a data steward (regular users can't archive)
        rdub_manager.rdub_manager.update_research_data_upload_box.side_effect = (
            RDUBManagerPort.BoxAccessError()
        )
        response = await rest_client.patch(
            url, json=request_data, headers=user_auth_headers
        )
        assert response.status_code == 403

        # normal response with data steward role
        rdub_manager.reset_mock()
        rdub_manager.rdub_manager.update_research_data_upload_box.side_effect = None
        rdub_manager.rdub_manager.update_research_data_upload_box.return_value = None
        response = await rest_client.patch(
            url, json=request_data, headers=ds_auth_headers
        )
        assert response.status_code == 204

        # handle archival prerequisites error from core
        rdub_manager.reset_mock()
        rdub_manager.rdub_manager.update_research_data_upload_box.side_effect = (
            RDUBManagerPort.ArchivalPrereqsError()
        )
        response = await rest_client.patch(
            url, json=request_data, headers=ds_auth_headers
        )
        assert response.status_code == 409

        # handle other exception
        rdub_manager.reset_mock()
        rdub_manager.rdub_manager.update_research_data_upload_box.side_effect = (
            TypeError()
        )
        response = await rest_client.patch(
            url, json=request_data, headers=ds_auth_headers
        )
        assert response.status_code == 500


async def test_submit_accession_map(
    config: Config, ds_auth_headers, user_auth_headers, bad_auth_headers
):
    """Test the POST /upload-boxes/{box_id}/accessions endpoint"""
    rdub_manager = AsyncMock()
    async with (
        prepare_rest_app(config=config, ghga_registry_override=rdub_manager) as app,
        AsyncTestClient(app=app) as rest_client,
    ):
        url = f"/upload-boxes/{TEST_BOX_ID}/file-ids"
        request_data = {
            "box_version": 0,
            "mapping": {"GHGAF001": str(uuid4()), "GHGAF002": str(uuid4())},
            "study_id": "GHGA-STUDY-001",
        }

        # unauthenticated
        response = await rest_client.post(url, json=request_data)
        assert response.status_code == 401

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
        rdub_manager.rdub_manager.store_accession_map.return_value = None
        response = await rest_client.post(
            url, json=request_data, headers=ds_auth_headers
        )
        assert response.status_code == 204

        # handle accession map error from core
        rdub_manager.reset_mock()
        rdub_manager.rdub_manager.store_accession_map.side_effect = (
            RDUBManagerPort.AccessionMapError()
        )
        response = await rest_client.post(
            url, json=request_data, headers=ds_auth_headers
        )
        assert response.status_code == 400

        # handle box not found error from core
        rdub_manager.reset_mock()
        rdub_manager.rdub_manager.store_accession_map.side_effect = (
            RDUBManagerPort.BoxNotFoundError(box_id=TEST_BOX_ID)
        )
        response = await rest_client.post(
            url, json=request_data, headers=ds_auth_headers
        )
        assert response.status_code == 404

        # handle other exception
        rdub_manager.reset_mock()
        rdub_manager.rdub_manager.store_accession_map.side_effect = TypeError()
        response = await rest_client.post(
            url, json=request_data, headers=ds_auth_headers
        )
        assert response.status_code == 500
