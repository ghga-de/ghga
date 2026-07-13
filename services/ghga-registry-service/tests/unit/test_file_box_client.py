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

"""Unit tests for the file box client"""

import json
from uuid import UUID, uuid4

import httpx
import pytest
from ghga_service_commons.utils.jwt_helpers import decode_and_validate_token
from hexkit.utils import now_utc_ms_prec
from jwcrypto.jwk import JWK
from pytest_httpx import HTTPXMock

from rs.adapters.outbound.http import FileBoxClient
from rs.config import Config
from rs.core.models import FileUploadWithAccession
from tests.fixtures.utils import TEST_MAX_SIZE

pytestmark = pytest.mark.asyncio

TEST_BOX_ID = UUID("2735c960-5e15-45dc-b27a-59162fbb2fd7")


async def test_create_file_upload_box(
    config: Config, httpx_mock: HTTPXMock, httpx_client: httpx.AsyncClient
):
    """Test the create_file_upload_box function"""
    file_upload_box_client = FileBoxClient(config=config, httpx_client=httpx_client)
    httpx_mock.add_response(201, json=str(TEST_BOX_ID))
    box_id = await file_upload_box_client.create_file_upload_box(
        storage_alias="HD01", max_size=TEST_MAX_SIZE
    )
    assert box_id == TEST_BOX_ID, "Failed happy path"

    # Check off-normal status code
    httpx_mock.add_response(500, json="Some error occurred.")
    with pytest.raises(FileBoxClient.OperationError):
        await file_upload_box_client.create_file_upload_box(
            storage_alias="HD01", max_size=TEST_MAX_SIZE
        )

    # Check with successful status code but garbled response body
    httpx_mock.add_response(201, json="id123")
    with pytest.raises(FileBoxClient.OperationError):
        await file_upload_box_client.create_file_upload_box(
            storage_alias="HD01", max_size=TEST_MAX_SIZE
        )


async def test_lock_file_upload_box(
    config: Config, httpx_mock: HTTPXMock, httpx_client: httpx.AsyncClient
):
    """Test the lock_file_upload_box function"""
    file_upload_box_client = FileBoxClient(config=config, httpx_client=httpx_client)

    # Happy path - force defaults to False
    httpx_mock.add_response(204)
    await file_upload_box_client.lock_file_upload_box(box_id=TEST_BOX_ID, version=0)
    assert json.loads(httpx_mock.get_requests()[0].content) == {
        "version": 0,
        "state": "locked",
        "force": False,
    }

    # Make sure force=True is forwarded in the request body
    httpx_mock.add_response(204)
    await file_upload_box_client.lock_file_upload_box(
        box_id=TEST_BOX_ID, version=0, force=True
    )

    # Inspect the request body intercepted by httpx_mock
    assert json.loads(httpx_mock.get_requests()[1].content) == {
        "version": 0,
        "state": "locked",
        "force": True,
    }

    # 409 "boxVersionOutdated" -> FUBVersionError
    httpx_mock.add_response(409, json={"exception_id": "boxVersionOutdated"})
    with pytest.raises(FileBoxClient.FUBVersionError) as fub_version_err:
        await file_upload_box_client.lock_file_upload_box(box_id=TEST_BOX_ID, version=0)
    assert str(fub_version_err.value) == str(
        FileBoxClient.FUBVersionError(box_id=TEST_BOX_ID)
    )

    # Verify that 409 "boxStateError" is translated to an FUBStateError
    httpx_mock.add_response(409, json={"exception_id": "boxStateError"})
    with pytest.raises(FileBoxClient.FUBStateError) as fub_state_err:
        await file_upload_box_client.lock_file_upload_box(box_id=TEST_BOX_ID, version=0)
    fub_state_err_msg = (
        f"Cannot lock FileUploadBox {TEST_BOX_ID} because the box's state"
        + " prevents it. The RS and UCS box states might be out of sync."
    )
    assert str(fub_state_err.value) == fub_state_err_msg

    # 409 "incompleteUploads" -> FUBIncompleteUploadsError with list of file IDs
    incomplete_file_ids = [uuid4(), uuid4()]
    httpx_mock.add_response(
        409,
        json={
            "exception_id": "incompleteUploads",
            "data": {
                "incomplete_uploads": [
                    [str(fid), f"alias-{i}"]
                    for i, fid in enumerate(incomplete_file_ids)
                ]
            },
        },
    )
    with pytest.raises(FileBoxClient.FUBIncompleteUploadsError) as fub_uploads_err:
        await file_upload_box_client.lock_file_upload_box(box_id=TEST_BOX_ID, version=0)
    assert fub_uploads_err.value.incomplete_file_ids == incomplete_file_ids

    # Non-409, non-204 -> OperationError
    httpx_mock.add_response(500, json="Some error occurred.")
    with pytest.raises(FileBoxClient.OperationError):
        await file_upload_box_client.lock_file_upload_box(box_id=TEST_BOX_ID, version=0)


async def test_unlock_file_upload_box(
    config: Config, httpx_mock: HTTPXMock, httpx_client: httpx.AsyncClient
):
    """Test the unlock_file_upload_box function"""
    file_upload_box_client = FileBoxClient(config=config, httpx_client=httpx_client)
    httpx_mock.add_response(204)
    await file_upload_box_client.unlock_file_upload_box(
        box_id=TEST_BOX_ID, version=0
    )  # no error == success
    assert json.loads(httpx_mock.get_requests()[0].content) == {
        "version": 0,
        "state": "open",
    }

    # Verify that 409 "boxVersionOutdated" is translated to an FUBVersionError
    httpx_mock.add_response(409, json={"exception_id": "boxVersionOutdated"})
    with pytest.raises(FileBoxClient.FUBVersionError) as fub_version_err:
        await file_upload_box_client.unlock_file_upload_box(
            box_id=TEST_BOX_ID, version=0
        )
    assert str(fub_version_err.value) == str(
        FileBoxClient.FUBVersionError(box_id=TEST_BOX_ID)
    )

    # Verify that 409 "boxStateError" is translated to an FUBStateError
    httpx_mock.add_response(409, json={"exception_id": "boxStateError"})
    with pytest.raises(FileBoxClient.FUBStateError) as fub_state_err:
        await file_upload_box_client.unlock_file_upload_box(
            box_id=TEST_BOX_ID, version=0
        )
    fub_state_err_msg = (
        f"Cannot unlock FileUploadBox {TEST_BOX_ID} because the box's state"
        + " prevents it. The RS and UCS box states might be out of sync."
    )
    assert str(fub_state_err.value) == fub_state_err_msg

    # Check off-normal status code
    httpx_mock.add_response(500, json="Some error occurred.")
    with pytest.raises(FileBoxClient.OperationError):
        await file_upload_box_client.unlock_file_upload_box(
            box_id=TEST_BOX_ID, version=0
        )


def _make_file_uploads(count: int) -> list[FileUploadWithAccession]:
    """Build a list of distinct FileUploadWithAccession instances for testing."""
    return [
        FileUploadWithAccession(
            id=uuid4(),
            box_id=uuid4(),
            storage_alias="HD01",
            bucket_id="permanent",
            object_id=uuid4(),
            alias=f"test{i}",
            decrypted_sha256=f"checksum{i}",
            decrypted_size=1000 + i * 100,
            encrypted_size=1100 + i * 100,
            state="archived",
            state_updated=now_utc_ms_prec(),
            part_size=100,
        )
        for i in range(count)
    ]


async def test_get_file_upload_list(
    config: Config, httpx_mock: HTTPXMock, httpx_client: httpx.AsyncClient
):
    """Test the get_file_upload_list function returns a single page and total count."""
    file_upload_box_client = FileBoxClient(config=config, httpx_client=httpx_client)
    file_list_response = _make_file_uploads(3)
    httpx_mock.add_response(
        200,
        json={
            "items": [x.model_dump(mode="json") for x in file_list_response],
            "total_count": len(file_list_response),
        },
    )
    file_list, total_count = await file_upload_box_client.get_file_upload_list(
        box_id=TEST_BOX_ID, skip=5, limit=10, sort=["alias", "-state"]
    )
    assert file_list == file_list_response
    assert total_count == len(file_list_response)

    # Confirm skip/limit/sort were forwarded to the endpoint as query parameters.
    # sort must be forwarded as a single, non-exploded comma-separated value.
    request = httpx_mock.get_requests()[-1]
    assert request.url.params.get("skip") == "5"
    assert request.url.params.get("limit") == "10"
    assert request.url.params.get_list("sort") == ["alias,-state"]
    assert request.url.params.get("sort") == "alias,-state"
    # with_checksums defaults to False and is always forwarded
    assert request.url.params.get("with_checksums") == "false"

    # Confirm sort is omitted entirely when not provided, and that with_checksums=True
    # is forwarded when requested.
    httpx_mock.add_response(
        200,
        json={
            "items": [x.model_dump(mode="json") for x in file_list_response],
            "total_count": len(file_list_response),
        },
    )
    await file_upload_box_client.get_file_upload_list(
        box_id=TEST_BOX_ID, with_checksums=True
    )
    request = httpx_mock.get_requests()[-1]
    assert "sort" not in request.url.params
    assert request.url.params.get("with_checksums") == "true"

    # Check off-normal status code
    httpx_mock.add_response(500, json="Some error occurred.")
    with pytest.raises(FileBoxClient.OperationError):
        await file_upload_box_client.get_file_upload_list(box_id=TEST_BOX_ID)

    # Check with successful status code but garbled response body
    httpx_mock.add_response(200, json="id123")
    with pytest.raises(FileBoxClient.OperationError):
        await file_upload_box_client.get_file_upload_list(box_id=TEST_BOX_ID)

    # Check with empty page response
    httpx_mock.add_response(200, json={"items": [], "total_count": 0})
    file_list, total_count = await file_upload_box_client.get_file_upload_list(
        box_id=TEST_BOX_ID
    )
    assert file_list == []
    assert total_count == 0


async def test_get_file_upload_list_missing_box(
    config: Config,
    httpx_mock: HTTPXMock,
    httpx_client: httpx.AsyncClient,
):
    """Test that a 404 is softened to an empty list when missing_box_ok is set."""
    file_upload_box_client = FileBoxClient(config=config, httpx_client=httpx_client)
    httpx_mock.add_response(404, json={"exception_id": "boxNotFound"})
    file_list, total_count = await file_upload_box_client.get_file_upload_list(
        box_id=TEST_BOX_ID, missing_box_ok=True
    )
    assert file_list == []
    assert total_count == 0

    # Verify that 404 results in OperationError if missing_box_ok is set to False
    # (default)
    httpx_mock.add_response(404, json={"exception_id": "boxNotFound"})
    with pytest.raises(FileBoxClient.OperationError):
        await file_upload_box_client.get_file_upload_list(box_id=TEST_BOX_ID)


async def test_get_file_upload_list_with_none_checksums(
    config: Config, httpx_mock: HTTPXMock, httpx_client: httpx.AsyncClient
):
    """Verify the client parses file uploads when the owning service omits the per-part
    checksum lists.

    With `with_checksums=False` (the default) the owning service returns
    `encrypted_parts_md5` and `encrypted_parts_sha256` as None, so the RS must not break
    when those fields are null.
    """
    file_upload_box_client = FileBoxClient(config=config, httpx_client=httpx_client)
    file_list_response = _make_file_uploads(2)

    # Build the response body with the checksum lists explicitly set to None, mimicking
    # what the owning service returns when checksums are not requested.
    items = []
    for file_upload in file_list_response:
        item = file_upload.model_dump(mode="json")
        item["encrypted_parts_md5"] = None
        item["encrypted_parts_sha256"] = None
        items.append(item)

    httpx_mock.add_response(200, json={"items": items, "total_count": len(items)})
    file_list, total_count = await file_upload_box_client.get_file_upload_list(
        box_id=TEST_BOX_ID
    )
    assert total_count == len(items)
    assert file_list == file_list_response

    # Confirm the checksum fields came through as None rather than causing a failure
    for file_upload in file_list:
        assert file_upload.encrypted_parts_md5 is None
        assert file_upload.encrypted_parts_sha256 is None


async def test_get_file_upload_list_with_populated_checksums(
    config: Config, httpx_mock: HTTPXMock, httpx_client: httpx.AsyncClient
):
    """Verify the client parses file uploads when the owning service includes the
    per-part checksum lists. This is a regression test to verify that the old behavior,
    i.e. receiving the populated checksum lists, still works.
    """
    file_upload_box_client = FileBoxClient(config=config, httpx_client=httpx_client)
    file_list_response = _make_file_uploads(2)

    # Build the response body with distinct per-part checksum lists on each file upload,
    # mimicking what the owning service returns when checksums are requested.
    items = []
    expected_checksums = {}
    for index, file_upload in enumerate(file_list_response):
        md5 = [f"md5-{index}-{part}" for part in range(3)]
        sha256 = [f"sha256-{index}-{part}" for part in range(3)]
        expected_checksums[file_upload.id] = (md5, sha256)
        item = file_upload.model_dump(mode="json")
        item["encrypted_parts_md5"] = md5
        item["encrypted_parts_sha256"] = sha256
        items.append(item)

    httpx_mock.add_response(200, json={"items": items, "total_count": len(items)})
    file_list, total_count = await file_upload_box_client.get_file_upload_list(
        box_id=TEST_BOX_ID, with_checksums=True
    )
    assert total_count == len(items)

    # Confirm the checksum lists were parsed onto the correct file uploads
    for file_upload in file_list:
        expected_md5, expected_sha256 = expected_checksums[file_upload.id]
        assert file_upload.encrypted_parts_md5 == expected_md5
        assert file_upload.encrypted_parts_sha256 == expected_sha256


async def test_get_all_file_uploads(
    config: Config,
    httpx_mock: HTTPXMock,
    httpx_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    """Verify that get_all_file_uploads pages through the endpoint and concatenates
    every page into a single list.
    """
    # Shrink the page size so a handful of uploads spans multiple pages
    monkeypatch.setattr("rs.adapters.outbound.http.UCS_UPLOADS_PAGE_SIZE", 2)
    file_upload_box_client = FileBoxClient(config=config, httpx_client=httpx_client)
    file_list_response = _make_file_uploads(5)
    total_count = len(file_list_response)
    # Three pages: [0, 1], [2, 3], [4]
    for start in range(0, total_count, 2):
        httpx_mock.add_response(
            200,
            json={
                "items": [
                    x.model_dump(mode="json")
                    for x in file_list_response[start : start + 2]
                ],
                "total_count": total_count,
            },
        )
    file_list = await file_upload_box_client.get_all_file_uploads(
        box_id=TEST_BOX_ID, with_checksums=True
    )
    assert file_list == file_list_response

    # Confirm each page was requested with the expected skip/limit query params and that
    # with_checksums was forwarded on every page request.
    requests = httpx_mock.get_requests()
    assert [
        (r.url.params.get("skip"), r.url.params.get("limit")) for r in requests
    ] == [("0", "2"), ("2", "2"), ("4", "2")]
    assert all(r.url.params.get("with_checksums") == "true" for r in requests)


async def test_get_all_file_uploads_missing_box(
    config: Config, httpx_mock: HTTPXMock, httpx_client: httpx.AsyncClient
):
    """Test that a 404 is softened to an empty list when missing_box_ok is set."""
    file_upload_box_client = FileBoxClient(config=config, httpx_client=httpx_client)
    httpx_mock.add_response(404, json={"exception_id": "boxNotFound"})
    file_list = await file_upload_box_client.get_all_file_uploads(
        box_id=TEST_BOX_ID, missing_box_ok=True
    )
    assert file_list == []

    httpx_mock.add_response(404, json={"exception_id": "boxNotFound"})
    with pytest.raises(FileBoxClient.OperationError):
        file_list = await file_upload_box_client.get_all_file_uploads(
            box_id=TEST_BOX_ID, missing_box_ok=False
        )


async def test_archive_file_upload_box(
    config: Config, httpx_mock: HTTPXMock, httpx_client: httpx.AsyncClient
):
    """Test the archive_file_upload_box function"""
    file_upload_box_client = FileBoxClient(config=config, httpx_client=httpx_client)
    httpx_mock.add_response(204)
    await file_upload_box_client.archive_file_upload_box(
        box_id=TEST_BOX_ID, version=0
    )  # no error == success
    assert json.loads(httpx_mock.get_requests()[0].content) == {
        "version": 0,
        "state": "archived",
    }

    # Verify that 409 "boxVersionOutdated" is translated to an FUBVersionError
    httpx_mock.add_response(409, json={"exception_id": "boxVersionOutdated"})
    with pytest.raises(FileBoxClient.FUBVersionError) as fub_version_err:
        await file_upload_box_client.archive_file_upload_box(
            box_id=TEST_BOX_ID, version=0
        )
    assert str(fub_version_err.value) == str(
        FileBoxClient.FUBVersionError(box_id=TEST_BOX_ID)
    )

    # Verify that 409 "boxStateError" is translated to an FUBStateError
    httpx_mock.add_response(409, json={"exception_id": "boxStateError"})
    with pytest.raises(FileBoxClient.FUBStateError) as fub_state_err:
        await file_upload_box_client.archive_file_upload_box(
            box_id=TEST_BOX_ID, version=0
        )
    fub_state_err_msg = (
        f"Cannot archive FileUploadBox {TEST_BOX_ID} because the box's state"
        + " prevents it. The RS and UCS box states might be out of sync."
    )
    assert str(fub_state_err.value) == fub_state_err_msg

    # Check off-normal status code
    httpx_mock.add_response(500, json="Some error occurred.")
    with pytest.raises(FileBoxClient.OperationError):
        await file_upload_box_client.archive_file_upload_box(
            box_id=TEST_BOX_ID, version=0
        )


async def test_resize_file_upload_box(
    config: Config,
    httpx_mock: HTTPXMock,
    httpx_client: httpx.AsyncClient,
    work_order_jwk: JWK,
):
    """Test the resize_file_upload_box function"""
    file_upload_box_client = FileBoxClient(config=config, httpx_client=httpx_client)

    # Happy path - verify request body and WOT work_type/box_id
    httpx_mock.add_response(204)
    await file_upload_box_client.resize_file_upload_box(
        box_id=TEST_BOX_ID, version=0, max_size=TEST_MAX_SIZE
    )
    request = httpx_mock.get_requests()[0]
    assert json.loads(request.content) == {"version": 0, "max_size": TEST_MAX_SIZE}

    raw_token = request.headers["authorization"].removeprefix("Bearer ")
    wot_claims = decode_and_validate_token(raw_token, work_order_jwk)
    assert wot_claims["work_type"] == "resize"
    assert wot_claims["box_id"] == str(TEST_BOX_ID)

    # Make sure 409 "boxVersionOutdated" is translated as FUBVersionError
    httpx_mock.add_response(409, json={"exception_id": "boxVersionOutdated"})
    with pytest.raises(FileBoxClient.FUBVersionError) as fub_version_err:
        await file_upload_box_client.resize_file_upload_box(
            box_id=TEST_BOX_ID, version=0, max_size=TEST_MAX_SIZE
        )
    assert str(fub_version_err.value) == str(
        FileBoxClient.FUBVersionError(box_id=TEST_BOX_ID)
    )

    # Make sure 409 "boxMaxSizeTooLow" is translated as FUBMaxSizeTooLowError
    httpx_mock.add_response(409, json={"exception_id": "boxMaxSizeTooLow"})
    with pytest.raises(FileBoxClient.FUBMaxSizeTooLowError):
        await file_upload_box_client.resize_file_upload_box(
            box_id=TEST_BOX_ID, version=0, max_size=1
        )

    # Make sure any other non-204 response is translated as OperationError
    httpx_mock.add_response(500, json={"exception_id": "miscError"})
    with pytest.raises(FileBoxClient.OperationError):
        await file_upload_box_client.resize_file_upload_box(
            box_id=TEST_BOX_ID, version=0, max_size=TEST_MAX_SIZE
        )


async def test_delete_file_upload(
    config: Config,
    httpx_mock: HTTPXMock,
    httpx_client: httpx.AsyncClient,
    work_order_jwk: JWK,
):
    """Test the delete_file_upload function"""
    file_upload_box_client = FileBoxClient(config=config, httpx_client=httpx_client)
    test_file_id = uuid4()

    # Happy path - verify WOT work_type/box_id/file_id
    httpx_mock.add_response(204)
    await file_upload_box_client.delete_file_upload(
        box_id=TEST_BOX_ID, file_id=test_file_id
    )  # no error == success
    request = httpx_mock.get_requests()[0]
    raw_token = request.headers["authorization"].removeprefix("Bearer ")
    wot_claims = decode_and_validate_token(raw_token, work_order_jwk)
    assert wot_claims["work_type"] == "delete"
    assert wot_claims["box_id"] == str(TEST_BOX_ID)
    assert wot_claims["file_id"] == str(test_file_id)

    # Make sure 409/boxStateError is translated as FUBStateError
    httpx_mock.add_response(409, json={"exception_id": "boxStateError"})
    with pytest.raises(FileBoxClient.FUBStateError) as fub_state_err:
        await file_upload_box_client.delete_file_upload(
            box_id=TEST_BOX_ID, file_id=test_file_id
        )
    fub_state_err_msg = (
        f"Cannot delete file from FileUploadBox {TEST_BOX_ID} because the box's state"
        + " prevents it. The RS and UCS box states might be out of sync."
    )
    assert str(fub_state_err.value) == fub_state_err_msg

    # Make sure 400, 404, and 500 are translated as OperationError
    for status_code in (400, 404, 500):
        httpx_mock.add_response(status_code, json="Some error occurred.")
        with pytest.raises(FileBoxClient.OperationError):
            await file_upload_box_client.delete_file_upload(
                box_id=TEST_BOX_ID, file_id=test_file_id
            )


async def test_delete_file_upload_box(
    config: Config,
    httpx_mock: HTTPXMock,
    httpx_client: httpx.AsyncClient,
    work_order_jwk: JWK,
):
    """Test the delete_file_upload_box function"""
    file_upload_box_client = FileBoxClient(config=config, httpx_client=httpx_client)

    # Set the UCS response to be 204
    httpx_mock.add_response(204)
    await file_upload_box_client.delete_file_upload_box(box_id=TEST_BOX_ID, version=0)
    request = httpx_mock.get_requests()[0]

    # Verify basic request details
    assert request.method == "DELETE"
    assert request.url.path.endswith(f"/boxes/{TEST_BOX_ID}")

    # Verify that the FUB version is set as a query parameter
    assert request.url.params["version"] == "0"

    # Inspect/verify the WOT details
    raw_token = request.headers["authorization"].removeprefix("Bearer ")
    wot_claims = decode_and_validate_token(raw_token, work_order_jwk)
    assert wot_claims["work_type"] == "delete_box"
    assert wot_claims["box_id"] == str(TEST_BOX_ID)
    assert "file_id" not in wot_claims

    # Verify that 404 (boxNotFound) is treated as success so retries are idempotent
    httpx_mock.add_response(404, json={"exception_id": "boxNotFound"})
    await file_upload_box_client.delete_file_upload_box(box_id=TEST_BOX_ID, version=0)

    # Verify that 409 "boxVersionOutdated" is translated to an FUBVersionError
    httpx_mock.add_response(409, json={"exception_id": "boxVersionOutdated"})
    with pytest.raises(FileBoxClient.FUBVersionError) as fub_version_err:
        await file_upload_box_client.delete_file_upload_box(
            box_id=TEST_BOX_ID, version=0
        )
    assert str(fub_version_err.value) == str(
        FileBoxClient.FUBVersionError(box_id=TEST_BOX_ID)
    )

    # Verify that 409 "boxStateError" is translated to an FUBStateError
    httpx_mock.add_response(409, json={"exception_id": "boxStateError"})
    with pytest.raises(FileBoxClient.FUBStateError) as fub_state_err:
        await file_upload_box_client.delete_file_upload_box(
            box_id=TEST_BOX_ID, version=0
        )
    fub_state_err_msg = (
        f"Cannot delete FileUploadBox {TEST_BOX_ID} because the box's state"
        + " prevents it. The RS and UCS box states might be out of sync."
    )
    assert str(fub_state_err.value) == fub_state_err_msg

    # Make sure other status codes result in an OperationError
    for status_code in (400, 500):
        httpx_mock.add_response(status_code, json="Some error occurred.")
        with pytest.raises(FileBoxClient.OperationError):
            await file_upload_box_client.delete_file_upload_box(
                box_id=TEST_BOX_ID, version=0
            )
