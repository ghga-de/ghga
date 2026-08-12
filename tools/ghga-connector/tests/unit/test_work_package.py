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

"""Unit tests for Work Package operations"""

import crypt4gh.keys
import pytest
from pydantic import SecretBytes

from ghga_connector import exceptions
from ghga_connector.core.client import async_client
from ghga_connector.core.work_package import WorkPackageClient
from tests.fixtures import set_runtime_test_config  # noqa: F401
from tests.fixtures.mock_api.apis import (
    MockApis,
    WorkPackageApiMock,
    mock_apis,  # noqa: F401
)
from tests.fixtures.mock_api.router import respond
from tests.fixtures.utils import (
    PRIVATE_KEY_FILE,
    mock_work_package_token,
    patch_work_package_functions,  # noqa: F401
)

pytestmark = [pytest.mark.asyncio]

FILES = {"file_1": ".tar.gz"}


@pytest.fixture()
def work_package_api(
    mock_apis: MockApis,  # noqa: F811
    set_runtime_test_config,  # noqa: F811
) -> WorkPackageApiMock:
    """The Work Package API mock, with the connector pointed at it."""
    return mock_apis.work_package


@pytest.mark.parametrize(
    "status_code, expected_error",
    [
        (200, None),
        (403, exceptions.NoWorkPackageAccessError),
        (500, exceptions.InvalidWorkPackageResponseError),
        (501, exceptions.InvalidWorkPackageResponseError),
    ],
)
async def test_get_work_package_file_info(
    status_code: int,
    expected_error: type[Exception] | None,
    work_package_api: WorkPackageApiMock,
    monkeypatch,
):
    """Test response handling with some mock - just make sure code paths work"""
    private_key = SecretBytes(crypt4gh.keys.get_private_key(PRIVATE_KEY_FILE, ""))
    monkeypatch.setattr(
        "ghga_connector.core.work_package.get_work_package_token",
        mock_work_package_token,
    )

    work_package_api.on_get_work_package = respond(status_code, json={"files": FILES})

    async with async_client() as client:
        work_package_client = WorkPackageClient(
            client=client,
            my_private_key=private_key,
            my_public_key=b"",  # doesn't matter for this test
        )

        if expected_error is None:
            assert await work_package_client.get_package_files() == FILES
        else:
            with pytest.raises(expected_error):
                await work_package_client.get_package_files()
