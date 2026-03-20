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

"""Unit tests for the API"""

from uuid import uuid4

import pytest
from jwcrypto.jwk import JWK

from rs.adapters.inbound.fastapi_.rest_models import FileIdMappingRequest
from rs.config import Config
from tests.fixtures import AppFixture, utils

pytestmark = pytest.mark.asyncio


async def test_create_box_endpoint_auth(
    config: Config, uos_jwk: JWK, app_fixture: AppFixture
):
    """Test that the endpoint returns a 401 if auth is not supplied or is invalid,
    a 401 if the work type is incorrect,
    and a 200 if the token is correct (and request succeeds).
    """
    study_pid = "test-study-1"
    mapping_request = FileIdMappingRequest(
        study_pid=study_pid, mapping={"GHGAF001": uuid4(), "GHGAF002": uuid4()}
    )
    body = mapping_request.model_dump(mode="json")
    rest_client = app_fixture.rest_client
    core_mock = app_fixture.core_mock

    url = f"/file-ids/{study_pid}"
    response = await rest_client.post(url, json=body)
    assert response.status_code == 401

    # Mismatched study pid should trigger a 403
    wrong_study_header = utils.map_file_ids_token_header(
        uos_jwk=uos_jwk, study_pid="some-other-study"
    )
    response = await rest_client.post(url, json=body, headers=wrong_study_header)
    assert response.status_code == 403

    # Correct auth should call the right core method and return 204
    good_token_header = utils.map_file_ids_token_header(
        uos_jwk=uos_jwk, study_pid=study_pid
    )
    response = await rest_client.post(url, json=body, headers=good_token_header)
    assert response.status_code == 204
    core_mock.post_file_ids.assert_awaited_once_with(
        study_pid=study_pid, file_id_map=mapping_request.mapping
    )


async def test_create_box_endpoint_internal_error(
    uos_jwk: JWK, app_fixture: AppFixture
):
    """Test that exceptions raised by the core are translated into a 500 response."""
    study_pid = "test-study-1"
    mapping_request = FileIdMappingRequest(
        study_pid=study_pid, mapping={"GHGAF001": uuid4(), "GHGAF002": uuid4()}
    )
    body = mapping_request.model_dump(mode="json")
    rest_client = app_fixture.rest_client
    core_mock = app_fixture.core_mock

    core_mock.post_file_ids.side_effect = RuntimeError("unexpected core failure")

    url = f"/file-ids/{study_pid}"
    good_token_header = utils.map_file_ids_token_header(
        uos_jwk=uos_jwk, study_pid=study_pid
    )
    response = await rest_client.post(url, json=body, headers=good_token_header)
    assert response.status_code == 500
