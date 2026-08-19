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

"""Integration tests for the upload path"""

import json
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4

import httpx2
import pytest

from ghga_connector import exceptions
from ghga_connector.config import set_runtime_config
from ghga_connector.core.client import async_client
from ghga_connector.core.main import upload_files
from ghga_connector.core.uploading.structs import CoreFileInfo
from ghga_connector.core.utils import modify_for_debug
from ghga_service_commons.utils.temp_files import big_temp_file
from tests.fixtures.config import get_test_config
from tests.fixtures.mock_api.apis import (
    MockApis,
    mock_apis,  # noqa: F401
)
from tests.fixtures.mock_api.router import mock_health_checks
from tests.fixtures.s3 import S3Fixture, s3_fixture  # noqa: F401
from tests.fixtures.utils import (
    PRIVATE_KEY_FILE,
    PUBLIC_KEY_FILE,
    TEST_STORAGE_ALIAS1,
    patch_work_package_functions,  # noqa: F401
)

ALIAS = "test-file-1"
SIZE = 10 * 1024 * 1024
pytestmark = [pytest.mark.asyncio]


@pytest.fixture(scope="function", autouse=True)
def apply_test_config():
    """Apply default test config"""
    with patch("ghga_connector.config.CONFIG", get_test_config()):
        yield


class S3BackedUpload:
    """Runs the Upload API mock against a real multipart upload in the S3 fixture.

    Creating a file upload starts a multipart upload in `bucket_id`, requesting a part
    URL presigns against it, and completing the upload finishes it and checks the MD5
    the connector calculated against the one S3 reports. The object ID the Upload API
    made up along the way is available as `object_id` once the upload has started.
    """

    def __init__(self, s3: S3Fixture, *, bucket_id: str) -> None:
        self._s3 = s3
        self._bucket_id = bucket_id
        self._upload_id: str | None = None
        self.object_id: str | None = None

    def serve(self, upload_api) -> None:
        """Answer the Upload API mock's endpoints out of the S3 fixture."""
        upload_api.on_create_file_upload = self._create_file_upload
        upload_api.on_get_part_upload_url = self._get_part_upload_url
        upload_api.on_complete_file_upload = self._complete_file_upload

    async def _create_file_upload(
        self, request: httpx2.Request, **path_variables
    ) -> httpx2.Response:
        """Start a multipart upload for a newly made up object ID."""
        self.object_id = str(uuid4())
        self._upload_id = await self._s3.storage.init_multipart_upload(
            bucket_id=self._bucket_id, object_id=self.object_id
        )
        return httpx2.Response(
            201,
            json={
                "file_id": self.object_id,
                "alias": json.loads(request.read())["alias"],
                "storage_alias": TEST_STORAGE_ALIAS1,
            },
        )

    async def _get_part_upload_url(
        self, request: httpx2.Request, file_id: UUID, part_no: int, **path_variables
    ) -> httpx2.Response:
        """Presign an upload URL for the requested part of the multipart upload."""
        assert self._upload_id, "No multipart upload was started"
        url = await self._s3.storage.get_part_upload_url(
            bucket_id=self._bucket_id,
            object_id=str(file_id),
            upload_id=self._upload_id,
            part_number=part_no,
        )
        return httpx2.Response(200, json=url)

    async def _complete_file_upload(
        self, request: httpx2.Request, file_id: UUID, **path_variables
    ) -> httpx2.Response:
        """Finish the multipart upload and check the announced MD5 against S3."""
        assert self._upload_id, "No multipart upload was started"
        await self._s3.storage.complete_multipart_upload(
            upload_id=self._upload_id, bucket_id=self._bucket_id, object_id=str(file_id)
        )
        self._upload_id = None

        calculated_md5 = json.loads(request.read())["encrypted_md5"]
        etag = await self._s3.storage.get_object_etag(
            object_id=str(file_id), bucket_id=self._bucket_id
        )
        assert etag.strip('"') == calculated_md5, (
            f"Connector calculated {calculated_md5}, but S3 says it should be {etag}"
        )
        return httpx2.Response(204)


async def test_upload_journey(
    s3_fixture: S3Fixture,  # noqa: F811
    mock_apis: MockApis,  # noqa: F811
    monkeypatch,
    patch_work_package_functions,  # noqa: F811
):
    """Test the whole upload path"""
    bucket_id = s3_fixture.existing_buckets[0]
    monkeypatch.setattr(
        "ghga_connector.core.uploading.api_calls.is_service_healthy", lambda s: True
    )

    upload = S3BackedUpload(s3_fixture, bucket_id=bucket_id)
    upload.serve(mock_apis.upload)

    # create a big temp file
    with big_temp_file(SIZE) as file:
        actual_size = Path(file.name).stat().st_size
        file_info = CoreFileInfo(
            alias=ALIAS, path=Path(file.name), decrypted_size=actual_size
        )
        async with (
            async_client(purpose="upload") as client,
            set_runtime_config(client=client),
        ):
            await upload_files(
                client=client,
                core_file_info_list=[file_info],
                my_public_key_path=PUBLIC_KEY_FILE,
                my_private_key_path=PRIVATE_KEY_FILE,
                passphrase=None,
            )
        assert upload.object_id, "No object ID was captured during upload"
        object_size = await s3_fixture.storage.get_object_size(
            bucket_id=bucket_id, object_id=upload.object_id
        )
        assert object_size == file_info.encrypted_size


async def test_upload_bad_url(
    mock_apis: MockApis,  # noqa: F811
    monkeypatch,
    patch_work_package_functions,  # noqa: F811
):
    """Check that the right error is raised for a bad URL in the upload logic."""
    mock_health_checks(monkeypatch, reachable=False)
    with big_temp_file(SIZE) as file, pytest.raises(exceptions.ApiNotReachableError):
        actual_size = Path(file.name).stat().st_size
        modify_for_debug(debug=True)
        file_info = CoreFileInfo(
            alias=ALIAS, path=Path(file.name), decrypted_size=actual_size
        )
        async with (
            async_client(purpose="upload") as client,
            set_runtime_config(client=client),
        ):
            await upload_files(
                client=client,
                core_file_info_list=[file_info],
                my_public_key_path=PUBLIC_KEY_FILE,
                my_private_key_path=PRIVATE_KEY_FILE,
                passphrase=None,
            )
