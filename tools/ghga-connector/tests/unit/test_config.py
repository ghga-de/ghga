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
#

"""Tests for API Calls"""

from unittest.mock import patch

import pytest

from ghga_connector.config import (
    get_download_api_url,
    get_ghga_pubkey,
    get_upload_api_url,
    get_work_package_api_url,
    set_runtime_config,
)
from ghga_connector.core import async_client
from tests.fixtures import set_runtime_test_config  # noqa: F401
from tests.fixtures.config import get_test_config
from tests.fixtures.mock_api.app import (
    mock_external_calls,  # noqa: F401
)

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.httpx_mock(
        assert_all_responses_were_requested=False,
        can_send_already_matched_responses=True,
        should_mock=lambda request: True,
    ),
]


@pytest.fixture(scope="function", autouse=True)
def apply_test_config():
    """Apply default test config"""
    with patch("ghga_connector.config.CONFIG", get_test_config()):
        yield


async def test_set_runtime_config(mock_external_calls):  # noqa: F811
    """Test set_runtime_config and related code"""
    # Make a list of the ctx var retrieval functions
    ctx_var_getter_fns = [
        get_download_api_url,
        get_ghga_pubkey,
        get_upload_api_url,
        get_work_package_api_url,
    ]
    async with async_client() as client:
        # Verify that all the context vars are empty before calling config setup
        for func in ctx_var_getter_fns:
            with pytest.raises(ValueError):
                _ = func()

        # Set up runtime config
        async with set_runtime_config(client):
            # verify values are now set (from mock api)
            for func in ctx_var_getter_fns:
                value = func()
                assert isinstance(value, str)
                assert len(value) > 0
