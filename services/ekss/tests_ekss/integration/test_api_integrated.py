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
"""Integration tests for the API + core + vault client"""

import base64
import io
import os

import crypt4gh.header
import pytest
from ghga_service_commons.api.testing import AsyncTestClient

from ekss.inject import prepare_rest_app
from tests_ekss.fixtures.config import get_config
from tests_ekss.fixtures.keypair import KeypairFixture
from tests_ekss.fixtures.utils import make_secret_payload
from tests_ekss.fixtures.vault import VaultFixture

pytestmark = pytest.mark.asyncio()


async def test_post_secrets(*, keypair: KeypairFixture, vault_fixture: VaultFixture):
    """Test request response for POST /secrets endpoint with valid data"""
    # Generate a secret and then encode it and encrypt it
    file_secret, encrypted_secret = make_secret_payload(keypair.ekss_pk)

    # Set up an API client and post the secret
    config = get_config([vault_fixture.config, keypair.config])
    async with (
        prepare_rest_app(config=config) as app,
        AsyncTestClient(app=app) as client,
    ):
        response = await client.post(url="/secrets", content=encrypted_secret)
        assert response.status_code == 201
        body = response.json()
        assert body["secret_id"]

    # Verify that the secret ID can be used to fetch the secret and that it matches
    assert vault_fixture.adapter.get_secret(key=body["secret_id"]) == file_secret


async def test_get_envelope(keypair: KeypairFixture, vault_fixture: VaultFixture):
    """Test request response for GET /secrets/../envelopes/.. with valid data"""
    secret = os.urandom(32)
    secret_id = vault_fixture.adapter.store_secret(secret=secret)
    client_pk = base64.urlsafe_b64encode(keypair.user_pk).decode("utf-8")

    # Set up a test client and fetch the envelope
    config = get_config([vault_fixture.config, keypair.config])
    async with (
        prepare_rest_app(config=config) as app,
        AsyncTestClient(app=app) as client,
    ):
        response = await client.get(url=f"/secrets/{secret_id}/envelopes/{client_pk}")
        assert response.status_code == 200
        body = response.json()

    # Inspect the response body
    content = base64.b64decode(body["content"])
    assert content

    # Extract the secret from the envelope using the user's sec key and verify it matches
    keys = [(0, keypair.user_sk, None)]
    session_keys, _ = crypt4gh.header.deconstruct(infile=io.BytesIO(content), keys=keys)
    assert session_keys[0] == secret


async def test_wrong_id(keypair: KeypairFixture, vault_fixture: VaultFixture):
    """Test request response for DELETE /secrets/../envelopes/..  with invalid secret_id"""
    secret_id = "wrong_id"
    client_pk = base64.urlsafe_b64encode(keypair.user_pk).decode("utf-8")

    # Set up a test client and fetch the envelope
    config = get_config([vault_fixture.config, keypair.config])
    async with (
        prepare_rest_app(config=config) as app,
        AsyncTestClient(app=app) as client,
    ):
        response = await client.get(url=f"/secrets/{secret_id}/envelopes/{client_pk}")
        assert response.status_code == 404
        body = response.json()
        assert body["exception_id"] == "secretNotFoundError"
