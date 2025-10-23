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

"""Fixtures that are used in both integration and unit tests"""

import pytest_asyncio
from hexkit.utils import set_context_var

from ghga_connector.config import (
    download_api_url_var,
    ghga_pubkey_var,
    upload_api_url_var,
    work_package_api_url_var,
)

from .mock_api import UploadStatus  # noqa: F401
from .s3 import s3_fixture  # noqa: F401
from .state import FILES  # noqa: F401


@pytest_asyncio.fixture()
async def set_runtime_test_config():
    """Set runtime config to dummy values so httpx mock can be used without mock api"""
    async with (
        set_context_var(upload_api_url_var, "http://127.0.0.1/upload"),
        set_context_var(download_api_url_var, "http://127.0.0.1/download"),
        set_context_var(work_package_api_url_var, "http://127.0.0.1/work"),
        set_context_var(
            ghga_pubkey_var, "qx5g31H7rdsq7sgkew9ElkLIXvBje4RxDVcAHcJD8XY="
        ),
    ):
        yield
