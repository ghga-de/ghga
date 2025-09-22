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
"""Set up session-scope fixtures for tests."""

import pytest
from ghga_service_commons.auth.ghga import AuthConfig
from ghga_service_commons.utils import jwt_helpers
from hexkit.providers.akafka.testutils import (  # noqa: F401
    kafka_container_fixture,
    kafka_fixture,
)
from hexkit.providers.mongodb.testutils import (  # noqa: F401
    mongodb_container_fixture,
    mongodb_fixture,
)
from hexkit.providers.s3.testutils import (  # noqa: F401
    s3_container_fixture,
    s3_fixture,
)

from tests_ucs.fixtures import ConfigFixture
from tests_ucs.fixtures.config import get_config
from tests_ucs.fixtures.joint import joint_fixture  # noqa: F401


@pytest.fixture(name="config")
def config_fixture() -> ConfigFixture:
    """Generate config from test yaml along with an auth key and JWK"""
    wps_jwk = jwt_helpers.generate_jwk()
    wps_auth_key = wps_jwk.export(private_key=False)
    uos_jwk = jwt_helpers.generate_jwk()
    uos_auth_key = uos_jwk.export(private_key=False)
    wps_cfg = AuthConfig(auth_key=wps_auth_key, auth_check_claims={})
    uos_cfg = AuthConfig(auth_key=uos_auth_key, auth_check_claims={})
    config = get_config(wps_auth_config=wps_cfg, uos_auth_config=uos_cfg)
    return ConfigFixture(config=config, wps_jwk=wps_jwk, uos_jwk=uos_jwk)
