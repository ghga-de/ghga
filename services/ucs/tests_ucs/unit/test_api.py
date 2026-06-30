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

from dataclasses import dataclass
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
import pytest_asyncio
from ghga_service_commons.api.testing import AsyncTestClient

from tests_ucs.fixtures import ConfigFixture, utils
from ucs.adapters.inbound.fastapi_ import http_exceptions
from ucs.constants import MAX_PART_SIZE, MIN_PART_SIZE
from ucs.inject import prepare_rest_app
from ucs.ports.inbound.controller import UploadControllerPort

pytestmark = pytest.mark.asyncio()

TEST_BOX_ID = UUID("bf344cd4-0c1b-434a-93d1-36a11b6b02d9")
TEST_FILE_ID = UUID("6e384b9f-f1c0-4c49-ae51-cee097b2862a")
INVALID_HEADER: dict[str, str] = {"Authorization": "Bearer ab12"}


@dataclass
class AppFixture:
    """A fixture class with a rest client and core override mock"""

    rest_client: AsyncTestClient
    core_mock: AsyncMock


@pytest_asyncio.fixture()
async def app_fixture(config: ConfigFixture):
    """A fixture that yields a configured rest client and accessible core override"""
    core_mock = AsyncMock()
    async with (
        prepare_rest_app(config=config.config, core_override=core_mock) as app,
        AsyncTestClient(app=app) as rest_client,
    ):
        yield AppFixture(rest_client=rest_client, core_mock=core_mock)


async def test_create_box_endpoint_auth(config: ConfigFixture, app_fixture: AppFixture):
    """Test that the endpoint returns a 401 if auth is not supplied or is invalid,
    a 401 if the work type is incorrect,
    and a 200 if the token is correct (and request succeeds).
    """
    rs_jwk = config.rs_jwk
    body = {"storage_alias": "HD01", "max_size": 1073741824}
    rest_client = app_fixture.rest_client
    core_mock = app_fixture.core_mock
    core_mock.create_file_upload_box.return_value = TEST_BOX_ID

    response = await rest_client.post("/boxes", json=body)
    assert response.status_code == 401

    response = await rest_client.post("/boxes", json=body, headers=INVALID_HEADER)
    assert response.status_code == 401

    # generate a token with the wrong work type for this action
    bad_token_header = utils.change_file_box_token_header(jwk=rs_jwk)
    response = await rest_client.post("/boxes", json=body, headers=bad_token_header)
    assert response.status_code == 401

    good_token_header = utils.create_file_box_token_header(jwk=rs_jwk)
    response = await rest_client.post("/boxes", json=body, headers=good_token_header)
    assert response.status_code == 201


async def test_update_box_endpoint_auth(config: ConfigFixture, app_fixture: AppFixture):
    """Test that the endpoint returns a 401 if auth is not supplied or is invalid,
    a 403 if auth is supplied but for another resource/work type,
    and a 204 if the token is correct (and request succeeds).
    """
    rs_jwk = config.rs_jwk
    body = {"state": "locked", "version": 0}
    rest_client = app_fixture.rest_client

    # Missing auth header should result in a 401
    url = f"/boxes/{TEST_BOX_ID}"
    response = await rest_client.patch(url, json=body)
    assert response.status_code == 401

    # Invalid auth header should result in a 401
    response = await rest_client.patch(url, json=body, headers=INVALID_HEADER)
    assert response.status_code == 401

    # Supply a token with the correct work type but the wrong box ID -- should get a 403
    wrong_id_token_header = utils.change_file_box_token_header(jwk=rs_jwk)
    response = await rest_client.patch(url, json=body, headers=wrong_id_token_header)
    assert response.status_code == 403

    # Supply the wrong work type for the given state -- should return 403
    wrong_work_token_header = utils.change_file_box_token_header(
        box_id=TEST_BOX_ID, work_type="unlock", jwk=rs_jwk
    )
    response = await rest_client.patch(url, json=body, headers=wrong_work_token_header)
    assert response.status_code == 403

    # Now the happy case for state-only update
    good_token_header = utils.change_file_box_token_header(
        box_id=TEST_BOX_ID, jwk=rs_jwk
    )
    response = await rest_client.patch(url, json=body, headers=good_token_header)
    assert response.status_code == 204

    # max_size-only update requires "resize" work type
    resize_body = {"max_size": 1073741824, "version": 0}
    wrong_work_for_resize = utils.change_file_box_token_header(
        box_id=TEST_BOX_ID, work_type="lock", jwk=rs_jwk
    )
    response = await rest_client.patch(
        url, json=resize_body, headers=wrong_work_for_resize
    )
    assert response.status_code == 403

    # Test max_size update with right work type
    resize_token_header = utils.change_file_box_token_header(
        box_id=TEST_BOX_ID, work_type="resize", jwk=rs_jwk
    )
    response = await rest_client.patch(
        url, json=resize_body, headers=resize_token_header
    )
    assert response.status_code == 204

    # Pydantic model should cause 422 if both state and max_size are supplied
    combined_body = {"state": "locked", "max_size": 1073741824, "version": 0}
    response = await rest_client.patch(
        url, json=combined_body, headers=resize_token_header
    )
    assert response.status_code == 422

    # Omitting both state and max_size should return a 422 as well
    empty_body = {"version": 0}
    response = await rest_client.patch(url, json=empty_body, headers=good_token_header)
    assert response.status_code == 422


async def test_view_box_endpoint_auth(config: ConfigFixture, app_fixture: AppFixture):
    """Test that the endpoint returns a 401 if auth is not supplied or is invalid,
    a 403 if a structurally valid auth token is supplied but doesn't match the
    requested resource, and a 200 if the token is correct (and request succeeds).
    """
    rs_jwk = config.rs_jwk
    rest_client = app_fixture.rest_client
    core_mock = app_fixture.core_mock
    core_mock.get_box_file_info.return_value = ([], 0)

    url = f"/boxes/{TEST_BOX_ID}/uploads"
    response = await rest_client.get(url)
    assert response.status_code == 401

    response = await rest_client.get(url, headers=INVALID_HEADER)
    assert response.status_code == 401

    wrong_box_id = utils.view_file_box_token_header(jwk=rs_jwk)
    response = await rest_client.get(url, headers=wrong_box_id)
    assert response.status_code == 403

    # generate a different kind of token with otherwise correct params
    wrong_work_type = utils.change_file_box_token_header(jwk=rs_jwk, box_id=TEST_BOX_ID)
    response = await rest_client.get(url, headers=wrong_work_type)
    assert response.status_code == 401

    good_token_header = utils.view_file_box_token_header(jwk=rs_jwk, box_id=TEST_BOX_ID)
    response = await rest_client.get(url, headers=good_token_header)
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total_count"] == 0


async def test_get_box_uploads_response_format(
    config: ConfigFixture, app_fixture: AppFixture
):
    """Test that the endpoint returns the correct paginated response shape and
    forwards skip/limit query parameters to the controller correctly.
    """
    rs_jwk = config.rs_jwk
    rest_client = app_fixture.rest_client
    core_mock = app_fixture.core_mock
    token_header = utils.view_file_box_token_header(jwk=rs_jwk, box_id=TEST_BOX_ID)
    url = f"/boxes/{TEST_BOX_ID}/uploads"

    # Build two mock file uploads with different aliases
    file_upload_a = utils.make_file_upload(file_id=TEST_FILE_ID)
    file_upload_a.alias = "test0.bam"
    file_upload_a.box_id = TEST_BOX_ID
    file_upload_b = utils.make_file_upload()
    file_upload_b.alias = "test1.vcf"
    file_upload_b.box_id = TEST_BOX_ID

    # Test with default parameters (no skip/limit in query string)
    core_mock.get_box_file_info.return_value = ([file_upload_a, file_upload_b], 5)
    response = await rest_client.get(url, headers=token_header)
    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 5
    assert len(body["items"]) == 2
    assert body["items"][0]["alias"] == "test0.bam"
    assert body["items"][1]["alias"] == "test1.vcf"
    core_mock.get_box_file_info.assert_awaited_with(
        box_id=TEST_BOX_ID, skip=0, limit=50
    )

    # Test with skip and limit parameters explicitly set
    core_mock.get_box_file_info.return_value = ([file_upload_b], 5)
    response = await rest_client.get(
        url, params={"skip": 3, "limit": 1}, headers=token_header
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 5
    assert len(body["items"]) == 1
    assert body["items"][0]["alias"] == "test1.vcf"
    core_mock.get_box_file_info.assert_awaited_with(box_id=TEST_BOX_ID, skip=3, limit=1)

    # skip beyond all results  controller returns empty page but preserves total_count
    core_mock.get_box_file_info.return_value = ([], 5)
    response = await rest_client.get(url, params={"skip": 100}, headers=token_header)
    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 5
    assert body["items"] == []


async def test_get_box_uploads_invalid_params(
    config: ConfigFixture, app_fixture: AppFixture
):
    """Test that invalid skip/limit query parameters are rejected with 422."""
    rs_jwk = config.rs_jwk
    rest_client = app_fixture.rest_client
    core_mock = app_fixture.core_mock
    core_mock.get_box_file_info.return_value = ([], 0)
    token_header = utils.view_file_box_token_header(jwk=rs_jwk, box_id=TEST_BOX_ID)
    url = f"/boxes/{TEST_BOX_ID}/uploads"

    # skip must be >= 0
    response = await rest_client.get(url, params={"skip": -1}, headers=token_header)
    assert response.status_code == 422

    # limit must be <= 100
    response = await rest_client.get(url, params={"limit": 101}, headers=token_header)
    assert response.status_code == 422

    # limit must also be >=0
    response = await rest_client.get(url, params={"limit": -1}, headers=token_header)
    assert response.status_code == 422


async def test_create_file_upload_endpoint_auth(
    config: ConfigFixture, app_fixture: AppFixture
):
    """Test that the POST file upload endpoint returns a 401 if auth is not
    supplied or is invalid, a 403 if a structurally valid auth token is supplied
    but doesn't match the requested resource, and a 201 if the request succeeds.
    """
    wps_jwk = config.wps_jwk
    body = {
        "alias": "test_file",
        "decrypted_size": utils.DECRYPTED_SIZE,
        "encrypted_size": utils.ENCRYPTED_SIZE,
        "part_size": utils.PART_SIZE,
    }
    rest_client = app_fixture.rest_client
    core_mock = app_fixture.core_mock
    core_mock.initiate_file_upload.return_value = (TEST_FILE_ID, "HD01")

    url = f"/boxes/{TEST_BOX_ID}/uploads"
    response = await rest_client.post(url, json=body)
    assert response.status_code == 401

    response = await rest_client.post(url, json=body, headers=INVALID_HEADER)
    assert response.status_code == 401

    # generate a token with the wrong work type for this action
    bad_token_header = utils.close_file_token_header(
        box_id=TEST_BOX_ID,
        jwk=wps_jwk,
    )
    response = await rest_client.post(url, json=body, headers=bad_token_header)
    assert response.status_code == 401

    # generate a token with wrong box ID
    wrong_box_token_header = utils.create_file_token_header(
        alias="test_file", jwk=wps_jwk
    )
    response = await rest_client.post(url, json=body, headers=wrong_box_token_header)
    assert response.status_code == 403

    # generate a token with wrong alias
    wrong_alias_token_header = utils.create_file_token_header(
        box_id=TEST_BOX_ID, alias="different_file", jwk=wps_jwk
    )
    response = await rest_client.post(url, json=body, headers=wrong_alias_token_header)
    assert response.status_code == 403

    good_token_header = utils.create_file_token_header(
        box_id=TEST_BOX_ID, alias="test_file", jwk=wps_jwk
    )
    response = await rest_client.post(url, json=body, headers=good_token_header)
    assert response.status_code == 201
    assert response.json() == {
        "file_id": str(TEST_FILE_ID),
        "alias": body["alias"],
        "storage_alias": "HD01",
    }


@pytest.mark.parametrize("overwrite", [True, False])
async def test_create_file_upload_passes_overwrite_to_core(
    config: ConfigFixture, app_fixture: AppFixture, overwrite: bool
):
    """Test that the overwrite field from the request body is forwarded to the core."""
    wps_jwk = config.wps_jwk
    core_mock = app_fixture.core_mock
    core_mock.initiate_file_upload.return_value = (TEST_FILE_ID, "HD01")

    body = {
        "alias": "test_file",
        "decrypted_size": utils.DECRYPTED_SIZE,
        "encrypted_size": utils.ENCRYPTED_SIZE,
        "part_size": utils.PART_SIZE,
        "overwrite": overwrite,
    }
    good_token_header = utils.create_file_token_header(
        box_id=TEST_BOX_ID, alias="test_file", jwk=wps_jwk
    )
    response = await app_fixture.rest_client.post(
        f"/boxes/{TEST_BOX_ID}/uploads", json=body, headers=good_token_header
    )
    assert response.status_code == 201

    core_mock.initiate_file_upload.assert_called_once_with(
        box_id=TEST_BOX_ID,
        alias="test_file",
        decrypted_size=utils.DECRYPTED_SIZE,
        encrypted_size=utils.ENCRYPTED_SIZE,
        part_size=utils.PART_SIZE,
        overwrite=overwrite,
    )


async def test_get_file_part_upload_url_endpoint_auth(
    config: ConfigFixture, app_fixture: AppFixture
):
    """Test that the GET file part upload URL endpoint returns a 401 if auth is not
    supplied or is invalid, a 403 if a structurally valid auth token is supplied
    but doesn't match the requested resource, and a 200 if the request succeeds.
    """
    wps_jwk = config.wps_jwk
    rest_client = app_fixture.rest_client
    core_mock = app_fixture.core_mock
    core_mock.get_part_upload_url.return_value = "some-url-here"

    url = f"/boxes/{TEST_BOX_ID}/uploads/{TEST_FILE_ID}/parts/1"
    response = await rest_client.get(url, headers=INVALID_HEADER)
    assert response.status_code == 401

    response = await rest_client.get(url)
    assert response.status_code == 401

    wrong_box_token_header = utils.upload_file_token_header(
        file_id=TEST_FILE_ID, jwk=wps_jwk
    )
    response = await rest_client.get(url, headers=wrong_box_token_header)
    assert response.status_code == 403

    wrong_file_token_header = utils.upload_file_token_header(
        box_id=TEST_BOX_ID, jwk=wps_jwk
    )
    response = await rest_client.get(url, headers=wrong_file_token_header)
    assert response.status_code == 403

    # generate a different kind of token with otherwise correct params
    wrong_work_type_token_header = utils.close_file_token_header(
        box_id=TEST_BOX_ID, file_id=TEST_FILE_ID, jwk=wps_jwk
    )
    response = await rest_client.get(url, headers=wrong_work_type_token_header)
    assert response.status_code == 401

    good_token_header = utils.upload_file_token_header(
        box_id=TEST_BOX_ID, file_id=TEST_FILE_ID, jwk=wps_jwk
    )
    response = await rest_client.get(url, headers=good_token_header)
    assert response.status_code == 200

    # Make sure the core's refresh_upload_activity() method was called
    core_mock.refresh_upload_activity.assert_awaited_with(file_id=TEST_FILE_ID)


async def test_complete_file_upload_endpoint_auth(
    config: ConfigFixture, app_fixture: AppFixture
):
    """Test that the PATCH complete_file_upload endpoint returns a 401 if bearer token
    is absent or invalid, a 403 if the token is structurally valid but contains
    incorrect data, and a 204 if the request succeeds.
    """
    wps_jwk = config.wps_jwk
    body: dict = {
        "decrypted_sha256": "unencrypted_checksum",
        "encrypted_md5": "encrypted_checksum",
        "encrypted_parts_md5": ["abc123"],
        "encrypted_parts_sha256": ["def456"],
    }
    rest_client = app_fixture.rest_client
    url = f"/boxes/{TEST_BOX_ID}/uploads/{TEST_FILE_ID}"

    response = await rest_client.patch(url, json=body)
    assert response.status_code == 401

    response = await rest_client.patch(url, json=body, headers=INVALID_HEADER)
    assert response.status_code == 401

    # generate a token with wrong box ID
    wrong_box_token_header = utils.close_file_token_header(
        file_id=TEST_FILE_ID, jwk=wps_jwk
    )
    response = await rest_client.patch(url, json=body, headers=wrong_box_token_header)
    assert response.status_code == 403

    # generate a token with wrong file ID
    wrong_file_token_header = utils.close_file_token_header(
        box_id=TEST_BOX_ID, jwk=wps_jwk
    )
    response = await rest_client.patch(url, json=body, headers=wrong_file_token_header)
    assert response.status_code == 403

    # generate a token with wrong work type
    wrong_work_token_header = utils.upload_file_token_header(
        box_id=TEST_BOX_ID, file_id=TEST_FILE_ID, jwk=wps_jwk
    )
    response = await rest_client.patch(url, json=body, headers=wrong_work_token_header)
    assert response.status_code == 401

    good_token_header = utils.close_file_token_header(
        box_id=TEST_BOX_ID, file_id=TEST_FILE_ID, jwk=wps_jwk
    )
    response = await rest_client.patch(url, json=body, headers=good_token_header)
    assert response.status_code == 204


async def test_delete_file_endpoint_auth(
    config: ConfigFixture, app_fixture: AppFixture
):
    """Test that the delete file endpoint returns a 401 if auth is not supplied or is invalid,
    and a 403 if a structurally valid auth token is supplied but doesn't match the
    requested resource.
    """
    wps_jwk = config.wps_jwk
    rest_client = app_fixture.rest_client
    url = f"/boxes/{TEST_BOX_ID}/uploads/{TEST_FILE_ID}"

    response = await rest_client.delete(url, headers=INVALID_HEADER)
    assert response.status_code == 401

    response = await rest_client.delete(url)
    assert response.status_code == 401

    wrong_box_token_header = utils.delete_file_token_header(
        file_id=TEST_FILE_ID, jwk=wps_jwk
    )
    response = await rest_client.delete(url, headers=wrong_box_token_header)
    assert response.status_code == 403

    wrong_file_token_header = utils.delete_file_token_header(
        box_id=TEST_BOX_ID, jwk=wps_jwk
    )
    response = await rest_client.delete(url, headers=wrong_file_token_header)
    assert response.status_code == 403

    # generate a different kind of token with otherwise correct params
    wrong_work_type_token_header = utils.close_file_token_header(
        box_id=TEST_BOX_ID, file_id=TEST_FILE_ID, jwk=wps_jwk
    )
    response = await rest_client.delete(url, headers=wrong_work_type_token_header)
    assert response.status_code == 401

    good_token_header = utils.delete_file_token_header(
        box_id=TEST_BOX_ID, file_id=TEST_FILE_ID, jwk=wps_jwk
    )
    response = await rest_client.delete(url, headers=good_token_header)
    assert response.status_code == 204


async def test_delete_file_endpoint_accepts_rs_signed_token(
    config: ConfigFixture, app_fixture: AppFixture
):
    """Test that the delete file endpoint also accepts a DeleteFileWorkOrder signed
    with the RS key (used for manual deletion by the RS), in addition to the
    WPS-signed tokens covered by test_delete_file_endpoint_auth. Mismatched claims
    must still be rejected.
    """
    rs_jwk = config.rs_jwk
    rest_client = app_fixture.rest_client
    url = f"/boxes/{TEST_BOX_ID}/uploads/{TEST_FILE_ID}"

    # Specifying the wrong box should get a 403 even if token signature is valid
    wrong_box_token_header = utils.delete_file_token_header(
        file_id=TEST_FILE_ID, jwk=rs_jwk
    )
    response = await rest_client.delete(url, headers=wrong_box_token_header)
    assert response.status_code == 403

    # Should be able to successfully call the endpoint
    good_token_header = utils.delete_file_token_header(
        box_id=TEST_BOX_ID, file_id=TEST_FILE_ID, jwk=rs_jwk
    )
    response = await rest_client.delete(url, headers=good_token_header)
    assert response.status_code == 204


@pytest.mark.parametrize(
    "core_error, http_error",
    [
        (
            UploadControllerPort.UnknownStorageAliasError(storage_alias="HD01"),
            http_exceptions.HttpUnknownStorageAliasError(),
        ),
        (RuntimeError("Random error"), http_exceptions.HttpInternalError()),
    ],
    ids=["UnknownStorageAlias", "InternalError"],
)
async def test_create_box_endpoint_error_handling(
    config: ConfigFixture,
    core_error: Exception,
    http_error: Exception,
    app_fixture: AppFixture,
):
    """Test that the endpoint correctly translates errors from the core."""
    rs_jwk = config.rs_jwk
    body = {"storage_alias": "HD01", "max_size": 1073741824}
    rest_client = app_fixture.rest_client
    core_mock = app_fixture.core_mock
    core_mock.create_file_upload_box.side_effect = core_error
    token_header = utils.create_file_box_token_header(jwk=rs_jwk)
    response = await rest_client.post("/boxes", json=body, headers=token_header)
    assert response.json()["description"] == str(http_error)


@pytest.mark.parametrize(
    "core_error, http_error",
    [
        (
            UploadControllerPort.BoxNotFoundError(box_id=TEST_BOX_ID),
            http_exceptions.HttpBoxNotFoundError(box_id=TEST_BOX_ID),
        ),
        (
            UploadControllerPort.BoxVersionError(box_id=TEST_BOX_ID),
            http_exceptions.HttpBoxVersionError(box_id=TEST_BOX_ID),
        ),
        (
            UploadControllerPort.IncompleteUploadsError(
                box_id=TEST_BOX_ID, file_ids=[(TEST_FILE_ID, "test_file")]
            ),
            http_exceptions.HttpIncompleteUploadsError(
                box_id=TEST_BOX_ID, file_ids=[(TEST_FILE_ID, "test_file")]
            ),
        ),
        (RuntimeError("Random error"), http_exceptions.HttpInternalError()),
    ],
    ids=["BoxNotFound", "BoxVersionOutdated", "IncompleteUploads", "InternalError"],
)
async def test_update_box_endpoint_error_handling(
    config: ConfigFixture,
    core_error: Exception,
    http_error: Exception,
    app_fixture: AppFixture,
):
    """Test that the endpoint correctly translates errors from the core."""
    rs_jwk = config.rs_jwk
    body = {"state": "locked", "version": 0}
    rest_client = app_fixture.rest_client
    core_mock = app_fixture.core_mock
    core_mock.lock_file_upload_box.side_effect = core_error
    token_header = utils.change_file_box_token_header(box_id=TEST_BOX_ID, jwk=rs_jwk)
    response = await rest_client.patch(
        f"/boxes/{TEST_BOX_ID}",
        json=body,
        headers=token_header,
    )
    assert response.json()["description"] == str(http_error)


async def test_update_box_max_size_below_current_error_handling(
    config: ConfigFixture, app_fixture: AppFixture
):
    """Test that BoxMaxSizeTooLowError is correctly translated to HTTP 409."""
    rs_jwk = config.rs_jwk
    body = {"max_size": 100, "version": 0}
    rest_client = app_fixture.rest_client
    core_mock = app_fixture.core_mock
    core_mock.update_box_max_size.side_effect = (
        UploadControllerPort.BoxMaxSizeTooLowError(
            box_id=TEST_BOX_ID, max_size=100, current_size=200
        )
    )
    token_header = utils.change_file_box_token_header(
        box_id=TEST_BOX_ID, work_type="resize", jwk=rs_jwk
    )
    response = await rest_client.patch(
        f"/boxes/{TEST_BOX_ID}", json=body, headers=token_header
    )
    expected = http_exceptions.HttpMaxSizeTooLowError(
        box_id=TEST_BOX_ID, max_size=100, current_size=200
    )
    assert response.json()["description"] == str(expected)


@pytest.mark.parametrize(
    "core_error, http_error",
    [
        (
            UploadControllerPort.BoxNotFoundError(box_id=TEST_BOX_ID),
            http_exceptions.HttpBoxNotFoundError(box_id=TEST_BOX_ID),
        ),
        (
            UploadControllerPort.PaginationError(),
            http_exceptions.HttpPaginationError(),
        ),
        (RuntimeError("Random error"), http_exceptions.HttpInternalError()),
    ],
    ids=["BoxNotFound", "PaginationError", "InternalError"],
)
async def test_view_box_endpoint_error_handling(
    config: ConfigFixture,
    core_error: Exception,
    http_error: Exception,
    app_fixture: AppFixture,
):
    """Test that the endpoint correctly translates errors from the core."""
    rs_jwk = config.rs_jwk
    rest_client = app_fixture.rest_client
    core_mock = app_fixture.core_mock
    core_mock.get_box_file_info.side_effect = core_error
    token_header = utils.view_file_box_token_header(jwk=rs_jwk, box_id=TEST_BOX_ID)
    response = await rest_client.get(
        f"/boxes/{TEST_BOX_ID}/uploads",
        headers=token_header,
    )
    assert response.json()["description"] == str(http_error), response.json()


@pytest.mark.parametrize(
    "core_error, http_error",
    [
        (
            UploadControllerPort.BoxNotFoundError(box_id=TEST_BOX_ID),
            http_exceptions.HttpBoxNotFoundError(box_id=TEST_BOX_ID),
        ),
        (
            UploadControllerPort.BoxStateError(box_id=TEST_BOX_ID, box_state="locked"),
            http_exceptions.HttpBoxStateError(box_id=TEST_BOX_ID, box_state="locked"),
        ),
        (
            UploadControllerPort.FileUploadAlreadyExists(alias="test_file"),
            http_exceptions.HttpFileUploadAlreadyExistsError(alias="test_file"),
        ),
        (
            UploadControllerPort.UnknownStorageAliasError(storage_alias="HD01"),
            http_exceptions.HttpUnknownStorageAliasError(),
        ),
        (
            UploadControllerPort.UploadAlreadyInProgressError(
                file_id=TEST_FILE_ID, bucket_id="test-bucket"
            ),
            http_exceptions.HttpOrphanedMultipartUploadError(file_alias="test_file"),
        ),
        (RuntimeError("Random error"), http_exceptions.HttpInternalError()),
        (
            UploadControllerPort.BoxMaxSizeExceededError(
                box_id=TEST_BOX_ID, max_size=9001, current_size=8000
            ),
            http_exceptions.HttpBoxMaxSizeExceededError(
                box_id=TEST_BOX_ID,
                max_size=9001,
                current_size=8000,
                file_alias="test_file",
            ),
        ),
        (
            UploadControllerPort.TooManyOpenUploadsError(
                box_id=TEST_BOX_ID, max_concurrent=3
            ),
            http_exceptions.HttpTooManyOpenUploadsError(
                box_id=TEST_BOX_ID, max_concurrent=3
            ),
        ),
        (
            UploadControllerPort.PartSizeError(file_alias="test_file", part_size=1000),
            http_exceptions.HttpPartSizeError(file_alias="test_file", part_size=1000),
        ),
    ],
    ids=[
        "BoxNotFound",
        "LockedBox",
        "FileUploadAlreadyExists",
        "UnknownStorageAlias",
        "UploadAlreadyInProgressError",
        "InternalError",
        "BoxMaxSizeExceededError",
        "TooManyOpenUploadsError",
        "PartSizeError",
    ],
)
async def test_create_file_upload_endpoint_error_translation(
    config: ConfigFixture,
    core_error: Exception,
    http_error: Exception,
    app_fixture: AppFixture,
):
    """Test that the endpoint correctly translates errors from the core."""
    wps_jwk = config.wps_jwk
    body = {
        "alias": "test_file",
        "decrypted_size": utils.DECRYPTED_SIZE,
        "encrypted_size": utils.ENCRYPTED_SIZE,
        "part_size": utils.PART_SIZE,
    }
    rest_client = app_fixture.rest_client
    core_mock = app_fixture.core_mock
    core_mock.initiate_file_upload.side_effect = core_error
    token_header = utils.create_file_token_header(
        box_id=TEST_BOX_ID, alias="test_file", jwk=wps_jwk
    )
    response = await rest_client.post(
        f"/boxes/{TEST_BOX_ID}/uploads",
        json=body,
        headers=token_header,
    )
    assert response.json()["description"] == str(http_error)


@pytest.mark.parametrize(
    "encrypted_size", [utils.DECRYPTED_SIZE, utils.DECRYPTED_SIZE - 1]
)
async def test_create_file_upload_endpoint_model_validator(
    config: ConfigFixture, app_fixture: AppFixture, encrypted_size: int
):
    """Test that the model validator for the model required on the endpoint works.

    It should make sure that the `encrypted_size` is larger than `decrypted_size`.
    """
    wps_jwk = config.wps_jwk
    body = {
        "alias": "test_file",
        "decrypted_size": utils.DECRYPTED_SIZE,
        "encrypted_size": encrypted_size,
        "part_size": utils.PART_SIZE,
    }
    rest_client = app_fixture.rest_client
    token_header = utils.create_file_token_header(
        box_id=TEST_BOX_ID, alias="test_file", jwk=wps_jwk
    )
    response = await rest_client.post(
        f"/boxes/{TEST_BOX_ID}/uploads",
        json=body,
        headers=token_header,
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "part_size",
    [0, MIN_PART_SIZE - 1, MAX_PART_SIZE + 1],
    ids=["zero", "too_small", "too_large"],
)
async def test_create_file_upload_endpoint_part_size_validation(
    config: ConfigFixture, app_fixture: AppFixture, part_size: int
):
    """Test the validation for part_size"""
    wps_jwk = config.wps_jwk
    body = {
        "alias": "test_file",
        "decrypted_size": utils.DECRYPTED_SIZE,
        "encrypted_size": utils.ENCRYPTED_SIZE,
        "part_size": part_size,
    }
    rest_client = app_fixture.rest_client
    core_mock = app_fixture.core_mock
    core_mock.initiate_file_upload.side_effect = RuntimeError("Shouldn't call the core")
    token_header = utils.create_file_token_header(
        box_id=TEST_BOX_ID, alias="test_file", jwk=wps_jwk
    )
    response = await rest_client.post(
        f"/boxes/{TEST_BOX_ID}/uploads",
        json=body,
        headers=token_header,
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "core_error, http_error",
    [
        (
            UploadControllerPort.UnknownStorageAliasError(storage_alias="HD01"),
            http_exceptions.HttpUnknownStorageAliasError(),
        ),
        (
            UploadControllerPort.UploadSessionNotFoundError(
                bucket_id="test-bucket", s3_upload_id="test-upload-id"
            ),
            http_exceptions.HttpS3UploadNotFoundError(),
        ),
        (RuntimeError("Random error"), http_exceptions.HttpInternalError()),
    ],
    ids=[
        "UnknownStorageAlias",
        "UploadSessionNotFound",
        "InternalError",
    ],
)
async def test_get_file_part_upload_url_endpoint_error_handling(
    config: ConfigFixture,
    core_error: Exception,
    http_error: Exception,
    app_fixture: AppFixture,
):
    """Test that the endpoint correctly translates errors from the core."""
    wps_jwk = config.wps_jwk
    rest_client = app_fixture.rest_client
    core_mock = app_fixture.core_mock
    core_mock.get_part_upload_url.side_effect = core_error
    token_header = utils.upload_file_token_header(
        box_id=TEST_BOX_ID, file_id=TEST_FILE_ID, jwk=wps_jwk
    )
    response = await rest_client.get(
        f"/boxes/{TEST_BOX_ID}/uploads/{TEST_FILE_ID}/parts/1",
        headers=token_header,
    )
    assert response.json()["description"] == str(http_error)


@pytest.mark.parametrize(
    "core_error, http_error",
    [
        (
            UploadControllerPort.BoxNotFoundError(box_id=TEST_BOX_ID),
            http_exceptions.HttpBoxNotFoundError(box_id=TEST_BOX_ID),
        ),
        (
            UploadControllerPort.BoxStateError(box_id=TEST_BOX_ID, box_state="locked"),
            http_exceptions.HttpBoxStateError(box_id=TEST_BOX_ID, box_state="locked"),
        ),
        (
            UploadControllerPort.FileUploadNotFound(file_id=TEST_FILE_ID),
            http_exceptions.HttpFileUploadNotFoundError(file_id=TEST_FILE_ID),
        ),
        (
            UploadControllerPort.UploadCompletionError(
                file_id=TEST_FILE_ID,
                s3_upload_id="test-upload",
                bucket_id="test-bucket",
            ),
            http_exceptions.HttpUploadCompletionError(
                box_id=TEST_BOX_ID, file_id=TEST_FILE_ID
            ),
        ),
        (
            UploadControllerPort.UploadSizeMismatchError(file_id=TEST_FILE_ID),
            http_exceptions.HttpUploadSizeMismatchError(file_id=TEST_FILE_ID),
        ),
        (
            UploadControllerPort.FileUploadStateError(
                file_id=TEST_FILE_ID, details="cancelled"
            ),
            http_exceptions.HttpFileUploadStateError(file_id=TEST_FILE_ID),
        ),
        (RuntimeError("Random error"), http_exceptions.HttpInternalError()),
    ],
    ids=[
        "BoxNotFound",
        "LockedBox",
        "FileUploadNotFound",
        "UploadCompletionError",
        "UploadSizeMismatchError",
        "FileUploadStateError",
        "InternalError",
    ],
)
async def test_complete_file_upload_endpoint_error_translation(
    config: ConfigFixture,
    core_error: Exception,
    http_error: Exception,
    app_fixture: AppFixture,
):
    """Test that the endpoint correctly translates errors from the core."""
    wps_jwk = config.wps_jwk
    body: dict = {
        "decrypted_sha256": "unencrypted_checksum",
        "encrypted_md5": "encrypted_checksum",
        "encrypted_parts_md5": ["abc123"],
        "encrypted_parts_sha256": ["def456"],
    }
    rest_client = app_fixture.rest_client
    core_mock = app_fixture.core_mock
    core_mock.complete_file_upload.side_effect = core_error
    token_header = utils.close_file_token_header(
        box_id=TEST_BOX_ID, file_id=TEST_FILE_ID, jwk=wps_jwk
    )
    response = await rest_client.patch(
        f"/boxes/{TEST_BOX_ID}/uploads/{TEST_FILE_ID}",
        json=body,
        headers=token_header,
    )
    assert response.json()["description"] == str(http_error)


@pytest.mark.parametrize(
    "core_error, http_error",
    [
        (
            UploadControllerPort.BoxNotFoundError(box_id=TEST_BOX_ID),
            http_exceptions.HttpBoxNotFoundError(box_id=TEST_BOX_ID),
        ),
        (
            UploadControllerPort.BoxStateError(box_id=TEST_BOX_ID, box_state="locked"),
            http_exceptions.HttpBoxStateError(box_id=TEST_BOX_ID, box_state="locked"),
        ),
        (
            UploadControllerPort.UnknownStorageAliasError(storage_alias="HD01"),
            http_exceptions.HttpUnknownStorageAliasError(),
        ),
        (
            UploadControllerPort.FileUploadNotFound(file_id=TEST_FILE_ID),
            http_exceptions.HttpFileUploadNotFoundError(file_id=TEST_FILE_ID),
        ),
        (
            UploadControllerPort.UploadAbortError(
                file_id=TEST_FILE_ID,
                s3_upload_id="test-upload",
                bucket_id="test-bucket",
            ),
            http_exceptions.HttpUploadAbortError(),
        ),
        (RuntimeError("Random error"), http_exceptions.HttpInternalError()),
    ],
    ids=[
        "BoxNotFound",
        "LockedBox",
        "UnknownStorageAlias",
        "FileUploadNotFound",
        "UploadAbortError",
        "InternalError",
    ],
)
async def test_delete_file_endpoint_error_handling(
    config: ConfigFixture,
    core_error: Exception,
    http_error: Exception,
    app_fixture: AppFixture,
):
    """Test that the endpoint correctly translates errors from the core."""
    wps_jwk = config.wps_jwk
    rest_client = app_fixture.rest_client
    core_mock = app_fixture.core_mock
    core_mock.remove_file_upload.side_effect = core_error
    token_header = utils.delete_file_token_header(
        box_id=TEST_BOX_ID, file_id=TEST_FILE_ID, jwk=wps_jwk
    )
    response = await rest_client.delete(
        f"/boxes/{TEST_BOX_ID}/uploads/{TEST_FILE_ID}",
        headers=token_header,
    )
    assert response.json()["description"] == str(http_error)


async def test_delete_box_endpoint_auth(config: ConfigFixture, app_fixture: AppFixture):
    """Test that the delete box endpoint returns 401 with no/invalid auth, 403 with a
    mismatched box_id in the token, and 204 on success with a valid token.
    """
    rs_jwk = config.rs_jwk
    rest_client = app_fixture.rest_client
    core_mock = app_fixture.core_mock
    core_mock.remove_file_upload_box.return_value = None

    # No auth token = 401
    response = await rest_client.delete(f"/boxes/{TEST_BOX_ID}")
    assert response.status_code == 401

    # Invalid auth token = 401
    response = await rest_client.delete(f"/boxes/{TEST_BOX_ID}", headers=INVALID_HEADER)
    assert response.status_code == 401

    # Wrong work type (use a ChangeFileBoxWorkOrder token) = 401 too
    bad_token_header = utils.change_file_box_token_header(
        jwk=rs_jwk, box_id=TEST_BOX_ID, work_type="lock"
    )
    response = await rest_client.delete(
        f"/boxes/{TEST_BOX_ID}", headers=bad_token_header
    )
    assert response.status_code == 401

    # Correct work type but wrong box_id in token
    wrong_box_token_header = utils.delete_file_box_token_header(jwk=rs_jwk)
    response = await rest_client.delete(
        f"/boxes/{TEST_BOX_ID}", headers=wrong_box_token_header
    )
    assert response.status_code == 403

    # Correct token
    good_token_header = utils.delete_file_box_token_header(
        jwk=rs_jwk, box_id=TEST_BOX_ID
    )
    response = await rest_client.delete(
        f"/boxes/{TEST_BOX_ID}", headers=good_token_header
    )
    assert response.status_code == 204


async def test_delete_box_endpoint_version_param(
    config: ConfigFixture, app_fixture: AppFixture
):
    """Test that the optional 'version' query parameter is forwarded to the core,
    and that omitting it forwards None.
    """
    rs_jwk = config.rs_jwk
    rest_client = app_fixture.rest_client
    core_mock = app_fixture.core_mock
    core_mock.remove_file_upload_box.return_value = None
    token_header = utils.delete_file_box_token_header(jwk=rs_jwk, box_id=TEST_BOX_ID)

    # Delete the box
    response = await rest_client.delete(
        f"/boxes/{TEST_BOX_ID}", params={"version": 4}, headers=token_header
    )
    assert response.status_code == 204
    core_mock.remove_file_upload_box.assert_awaited_with(box_id=TEST_BOX_ID, version=4)

    # Delete the box but omit the version query param
    response = await rest_client.delete(f"/boxes/{TEST_BOX_ID}", headers=token_header)
    assert response.status_code == 204
    core_mock.remove_file_upload_box.assert_awaited_with(
        box_id=TEST_BOX_ID, version=None
    )


@pytest.mark.parametrize(
    "core_error, http_error",
    [
        (
            UploadControllerPort.BoxNotFoundError(box_id=TEST_BOX_ID),
            http_exceptions.HttpBoxNotFoundError(box_id=TEST_BOX_ID),
        ),
        (
            UploadControllerPort.BoxVersionError(box_id=TEST_BOX_ID),
            http_exceptions.HttpBoxVersionError(box_id=TEST_BOX_ID),
        ),
        (
            UploadControllerPort.BoxStateError(
                box_id=TEST_BOX_ID, box_state="archived"
            ),
            http_exceptions.HttpBoxStateError(box_id=TEST_BOX_ID, box_state="archived"),
        ),
        (
            UploadControllerPort.UploadAbortError(
                file_id=TEST_FILE_ID,
                s3_upload_id="test-upload",
                bucket_id="test-bucket",
            ),
            http_exceptions.HttpUploadAbortError(),
        ),
        (RuntimeError("Random error"), http_exceptions.HttpInternalError()),
    ],
    ids=[
        "BoxNotFound",
        "BoxVersionOutdated",
        "BoxStateError",
        "UploadAbortError",
        "InternalError",
    ],
)
async def test_delete_box_endpoint_error_handling(
    config: ConfigFixture,
    core_error: Exception,
    http_error: Exception,
    app_fixture: AppFixture,
):
    """Test that the endpoint correctly translates errors from the core."""
    rs_jwk = config.rs_jwk
    rest_client = app_fixture.rest_client
    core_mock = app_fixture.core_mock
    core_mock.remove_file_upload_box.side_effect = core_error
    token_header = utils.delete_file_box_token_header(jwk=rs_jwk, box_id=TEST_BOX_ID)
    response = await rest_client.delete(f"/boxes/{TEST_BOX_ID}", headers=token_header)
    assert response.json()["description"] == str(http_error)
