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

"""Utils for Fixture handling"""

from pathlib import Path
from unittest.mock import AsyncMock
from uuid import UUID

import crypt4gh.keys
import httpx
import pytest
from ghga_service_commons.utils import crypt

from ghga_connector.core.uploading.structs import CoreFileInfo, FileInfoForUpload

BASE_DIR = Path(__file__).parent.resolve()
KEY_DIR = BASE_DIR / "keypair"
PUBLIC_KEY_FILE = KEY_DIR / "key.pub"
PRIVATE_KEY_FILE = KEY_DIR / "key.sec"
TEST_STORAGE_ALIAS1 = "HD01"
TEST_STORAGE_ALIAS2 = "B"
TEST_RDUB_ID = UUID("fd4981eb-5272-4170-8a78-6ab17d92363d")
TEST_FUB_ID = UUID("6ec579af-3918-45d2-8333-d2cdcfb53d1d")
TEST_FILE_ID = UUID("550e8400-e29b-41d4-a716-446655440002")
TEST_WORK_PACKAGE_ID = "2cc323e2-f2ba-4f52-aae3-57107ab8ff2f"
TEST_PUBLIC_KEYS: dict[str, str] = {
    TEST_STORAGE_ALIAS1: "qx5g31H7rdsq7sgkew9ElkLIXvBje4RxDVcAHcJD8XY=",
    TEST_STORAGE_ALIAS2: "qx5g31H7rdsq7sgkew9ElkLIXvBje4RxDVcAHcJD8XY=",
}

DEFAULT_TEST_PART_SIZE = 5 * 1024 * 1024


def make_file_info_for_upload(
    *,
    path: Path,
    alias: str = "test-file",
    decrypted_size: int = 100,
) -> FileInfoForUpload:
    """Create a FileInfoForUpload instance for use in unit tests."""
    core = CoreFileInfo(alias=alias, path=path, decrypted_size=decrypted_size)
    return FileInfoForUpload(
        core_file_info=core, configured_part_size=DEFAULT_TEST_PART_SIZE
    )


@pytest.fixture()
def patch_work_package_functions(monkeypatch):
    """Patches work package functions for up and download as well as input"""
    box_ids_mock = AsyncMock()
    box_ids_mock.return_value = (TEST_RDUB_ID, TEST_FUB_ID)
    monkeypatch.setattr(
        "ghga_connector.core.work_package.WorkPackageClient.get_package_box_ids",
        box_ids_mock,
    )
    monkeypatch.setattr(
        "ghga_connector.core.work_package.get_work_package_token",
        mock_work_package_token,
    )
    monkeypatch.setattr(
        "ghga_connector.core.work_package._decrypt",
        lambda data, key: data,
    )


def mock_work_package_token(max_tries: int) -> list[str]:
    """Helper to mock user input"""
    token = "abcde"

    public_key = crypt4gh.keys.get_public_key(PUBLIC_KEY_FILE)

    work_package_parts = [TEST_WORK_PACKAGE_ID, crypt.encrypt(token, public_key)]
    return work_package_parts


class RecordingClient(httpx.AsyncClient):
    """An `AsyncClient` wrapper that records responses."""

    calls: list[httpx.Response]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calls = []

    async def _do_request(self, method: str, *args, **kwargs) -> httpx.Response:
        """Wrap actual client calls so we can see which calls were cached vs not."""
        method_func = getattr(super(), method)
        response = await method_func(*args, **kwargs)
        self.calls.append(response)
        return response

    async def get(self, *args, **kwargs) -> httpx.Response:
        """Record GET calls."""
        return await self._do_request("get", *args, **kwargs)

    async def post(self, *args, **kwargs) -> httpx.Response:
        """Record POST calls."""
        return await self._do_request("post", *args, **kwargs)
