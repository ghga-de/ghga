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

"""Import necessary test fixtures."""

import pytest
from hexkit.providers.s3.testutils import (  # noqa: F401
    s3_container_fixture,
    s3_fixture,
)

from dhfs.config import Config
from tests.fixtures.config import get_config
from tests.fixtures.joint import joint_fixture  # noqa: F401
from tests.fixtures.utils import (
    CENTRAL_CRYPT4GH_PUBLIC_KEY,
    DHFS_CRYPT4GH_PRIVATE_KEY_PATH,
    DHFS_SIGNING_KEY,
)


@pytest.fixture(name="config")
def config_fixture() -> Config:
    """Update the default config with the auth keys for FIS & DHFS"""
    return get_config(
        data_hub_crypt4gh_private_key_path=DHFS_CRYPT4GH_PRIVATE_KEY_PATH,
        data_hub_signing_key=DHFS_SIGNING_KEY,
        central_api_crypt4gh_public_key=CENTRAL_CRYPT4GH_PUBLIC_KEY,
    )
