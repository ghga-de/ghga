# Copyright 2021 Universität Tübingen, DKFZ and EMBL
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

"""A test dummy just to make the CI pass."""

import time

import pytest
from ghga_connector.cli import config
from ghga_connector.core.api_calls import get_file_metadata, get_upload_info

from src.run_upload_path import delegate_paths


@pytest.mark.asyncio
async def test_upload_path():
    """Test upload path"""
    unencrypted_id, encrypted_id = await delegate_paths()
    await check_status(file_id=unencrypted_id, expected_status="rejected")
    # <= 180 did not work in actions, so let's currently keep it this way
    time.sleep(240)
    await check_status(file_id=encrypted_id, expected_status="accepted")


async def check_status(*, file_id: str, expected_status: str):
    """Assert upload attempt state matches expected state"""
    metadata = get_file_metadata(api_url=config.upload_api, file_id=file_id)
    upload_id = metadata["latest_upload_id"]
    upload_attempt = get_upload_info(api_url=config.upload_api, upload_id=upload_id)
    assert upload_attempt["status"] == expected_status
