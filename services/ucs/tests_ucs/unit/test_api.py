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

from dataclasses import dataclass
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
import pytest_asyncio
from ghga_service_commons.api.testing import AsyncTestClient

from tests_ucs.fixtures import ConfigFixture, utils
from ucs.adapters.inbound.fastapi_ import http_exceptions
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
    uos_jwk = config.uos_jwk
    body = {"storage_alias": "HD01"}
    rest_client = app_fixture.rest_client
    core_mock = app_fixture.core_mock
    core_mock.create_file_upload_box.return_value = TEST_BOX_ID

    response = await rest_client.post("/boxes", json=body)
    assert response.status_code == 401

    response = await rest_client.post("/boxes", json=body, headers=INVALID_HEADER)
    assert response.status_code == 401

    # generate a token with the wrong work type for this action
    bad_token_header = utils.change_file_box_token_header(jwk=uos_jwk)
    response = await rest_client.post("/boxes", json=body, headers=bad_token_header)
    assert response.status_code == 401

    good_token_header = utils.create_file_box_token_header(jwk=uos_jwk)
    response = await rest_client.post("/boxes", json=body, headers=good_token_header)
    assert response.status_code == 201


async def test_update_box_endpoint_auth(config: ConfigFixture, app_fixture: AppFixture):
    """Test that the endpoint returns a 401 if auth is not supplied or is invalid,
    a 403 if auth is supplied but for another resource/work type,
    and a 204 if the token is correct (and request succeeds).
    """
    uos_jwk = config.uos_jwk
    body = {"lock": True}
    rest_client = app_fixture.rest_client

    url = f"/boxes/{TEST_BOX_ID}"
    response = await rest_client.patch(url, json=body)
    assert response.status_code == 401

    response = await rest_client.patch(url, json=body, headers=INVALID_HEADER)
    assert response.status_code == 401

    wrong_id_token_header = utils.change_file_box_token_header(jwk=uos_jwk)
    response = await rest_client.patch(url, json=body, headers=wrong_id_token_header)
    assert response.status_code == 403

    # generate a different kind of token with otherwise correct params
    wrong_work_token_header = utils.change_file_box_token_header(
        box_id=TEST_BOX_ID, work_type="unlock", jwk=uos_jwk
    )
    response = await rest_client.patch(url, json=body, headers=wrong_work_token_header)
    assert response.status_code == 401

    good_token_header = utils.change_file_box_token_header(
        box_id=TEST_BOX_ID, jwk=uos_jwk
    )
    response = await rest_client.patch(url, json=body, headers=good_token_header)
    assert response.status_code == 204


async def test_view_box_endpoint_auth(config: ConfigFixture, app_fixture: AppFixture):
    """Test that the endpoint returns a 401 if auth is not supplied or is invalid,
    a 403 if a structurally valid auth token is supplied but doesn't match the
    requested resource, and a 200 if the token is correct (and request succeeds).
    """
    uos_jwk = config.uos_jwk
    rest_client = app_fixture.rest_client

    url = f"/boxes/{TEST_BOX_ID}/uploads"
    response = await rest_client.get(url)
    assert response.status_code == 401

    response = await rest_client.get(url, headers=INVALID_HEADER)
    assert response.status_code == 401

    wrong_box_id = utils.view_file_box_token_header(jwk=uos_jwk)
    response = await rest_client.get(url, headers=wrong_box_id)
    assert response.status_code == 403

    # generate a different kind of token with otherwise correct params
    wrong_work_type = utils.change_file_box_token_header(
        jwk=uos_jwk, box_id=TEST_BOX_ID
    )
    response = await rest_client.get(url, headers=wrong_work_type)
    assert response.status_code == 401

    good_token_header = utils.view_file_box_token_header(
        jwk=uos_jwk, box_id=TEST_BOX_ID
    )
    response = await rest_client.get(url, headers=good_token_header)
    assert response.status_code == 200


async def test_create_file_upload_endpoint_auth(
    config: ConfigFixture, app_fixture: AppFixture
):
    """Test that the POST file upload endpoint returns a 401 if auth is not
    supplied or is invalid, a 403 if a structurally valid auth token is supplied
    but doesn't match the requested resource, and a 201 if the request succeeds.
    """
    wps_jwk = config.wps_jwk
    body = {"alias": "test_file", "size": 1024}
    rest_client = app_fixture.rest_client
    core_mock = app_fixture.core_mock
    core_mock.initiate_file_upload.return_value = TEST_FILE_ID

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


async def test_complete_file_upload_endpoint_auth(
    config: ConfigFixture, app_fixture: AppFixture
):
    """Test that the PATCH complete_file_upload endpoint returns a 401 if bearer token
    is absent or invalid, a 403 if the token is structurally valid but contains
    incorrect data, and a 204 if the request succeeds.
    """
    wps_jwk = config.wps_jwk
    body: dict[str, str] = {"checksum": "md5checksumhere"}
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
    uos_jwk = config.uos_jwk
    body = {"storage_alias": "HD01"}
    rest_client = app_fixture.rest_client
    core_mock = app_fixture.core_mock
    core_mock.create_file_upload_box.side_effect = core_error
    token_header = utils.create_file_box_token_header(jwk=uos_jwk)
    response = await rest_client.post("/boxes", json=body, headers=token_header)
    assert response.json()["description"] == str(http_error)


@pytest.mark.parametrize(
    "core_error, http_error",
    [
        (
            UploadControllerPort.BoxNotFoundError(box_id=TEST_BOX_ID),
            http_exceptions.HttpBoxNotFoundError(box_id=TEST_BOX_ID),
        ),
        (RuntimeError("Random error"), http_exceptions.HttpInternalError()),
    ],
    ids=["BoxNotFound", "InternalError"],
)
async def test_update_box_endpoint_error_handling(
    config: ConfigFixture,
    core_error: Exception,
    http_error: Exception,
    app_fixture: AppFixture,
):
    """Test that the endpoint correctly translates errors from the core."""
    uos_jwk = config.uos_jwk
    body = {"lock": True}
    rest_client = app_fixture.rest_client
    core_mock = app_fixture.core_mock
    core_mock.lock_file_upload_box.side_effect = core_error
    token_header = utils.change_file_box_token_header(box_id=TEST_BOX_ID, jwk=uos_jwk)
    response = await rest_client.patch(
        f"/boxes/{TEST_BOX_ID}",
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
        (RuntimeError("Random error"), http_exceptions.HttpInternalError()),
    ],
    ids=["BoxNotFound", "InternalError"],
)
async def test_view_box_endpoint_error_handling(
    config: ConfigFixture,
    core_error: Exception,
    http_error: Exception,
    app_fixture: AppFixture,
):
    """Test that the endpoint correctly translates errors from the core."""
    uos_jwk = config.uos_jwk
    rest_client = app_fixture.rest_client
    core_mock = app_fixture.core_mock
    core_mock.get_file_ids_for_box.side_effect = core_error
    token_header = utils.view_file_box_token_header(jwk=uos_jwk, box_id=TEST_BOX_ID)
    response = await rest_client.get(
        f"/boxes/{TEST_BOX_ID}/uploads",
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
            UploadControllerPort.LockedBoxError(box_id=TEST_BOX_ID),
            http_exceptions.HttpLockedBoxError(box_id=TEST_BOX_ID),
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
            UploadControllerPort.OrphanedMultipartUploadError(
                file_id=TEST_FILE_ID, bucket_id="test-bucket"
            ),
            http_exceptions.HttpOrphanedMultipartUploadError(file_alias="test_file"),
        ),
        (RuntimeError("Random error"), http_exceptions.HttpInternalError()),
    ],
    ids=[
        "BoxNotFound",
        "LockedBox",
        "FileUploadAlreadyExists",
        "UnknownStorageAlias",
        "OrphanedMultipartUploadError",
        "InternalError",
    ],
)
async def test_create_file_upload_endpoint_error_handling(
    config: ConfigFixture,
    core_error: Exception,
    http_error: Exception,
    app_fixture: AppFixture,
):
    """Test that the endpoint correctly translates errors from the core."""
    wps_jwk = config.wps_jwk
    body = {"alias": "test_file", "size": 1024}
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
    "core_error, http_error",
    [
        (
            UploadControllerPort.S3UploadDetailsNotFoundError(file_id=TEST_FILE_ID),
            http_exceptions.HttpS3UploadDetailsNotFoundError(file_id=TEST_FILE_ID),
        ),
        (
            UploadControllerPort.UnknownStorageAliasError(storage_alias="HD01"),
            http_exceptions.HttpUnknownStorageAliasError(),
        ),
        (
            UploadControllerPort.S3UploadNotFoundError(
                bucket_id="test-bucket", s3_upload_id="test-upload-id"
            ),
            http_exceptions.HttpS3UploadNotFoundError(),
        ),
        (RuntimeError("Random error"), http_exceptions.HttpInternalError()),
    ],
    ids=[
        "S3UploadDetailsNotFound",
        "UnknownStorageAlias",
        "S3UploadNotFound",
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
            UploadControllerPort.LockedBoxError(box_id=TEST_BOX_ID),
            http_exceptions.HttpLockedBoxError(box_id=TEST_BOX_ID),
        ),
        (
            UploadControllerPort.FileUploadNotFound(file_id=TEST_FILE_ID),
            http_exceptions.HttpFileUploadNotFoundError(file_id=TEST_FILE_ID),
        ),
        (
            UploadControllerPort.S3UploadDetailsNotFoundError(file_id=TEST_FILE_ID),
            http_exceptions.HttpS3UploadDetailsNotFoundError(file_id=TEST_FILE_ID),
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
        (RuntimeError("Random error"), http_exceptions.HttpInternalError()),
    ],
    ids=[
        "BoxNotFound",
        "LockedBox",
        "FileUploadNotFound",
        "S3UploadDetailsNotFound",
        "UploadCompletionError",
        "InternalError",
    ],
)
async def test_complete_file_upload_endpoint_error_handling(
    config: ConfigFixture,
    core_error: Exception,
    http_error: Exception,
    app_fixture: AppFixture,
):
    """Test that the endpoint correctly translates errors from the core."""
    wps_jwk = config.wps_jwk
    body: dict[str, str] = {"checksum": "sha256:abc123"}
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
            UploadControllerPort.LockedBoxError(box_id=TEST_BOX_ID),
            http_exceptions.HttpLockedBoxError(box_id=TEST_BOX_ID),
        ),
        (
            UploadControllerPort.S3UploadDetailsNotFoundError(file_id=TEST_FILE_ID),
            http_exceptions.HttpS3UploadDetailsNotFoundError(file_id=TEST_FILE_ID),
        ),
        (
            UploadControllerPort.UnknownStorageAliasError(storage_alias="HD01"),
            http_exceptions.HttpUnknownStorageAliasError(),
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
        "S3UploadDetailsNotFound",
        "UnknownStorageAlias",
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
