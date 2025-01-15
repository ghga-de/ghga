# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
"""Checking if GET on /secrets/{secret_id}/envelopes/{client_pk} works correctly"""

import base64
import io

import crypt4gh.header
import pytest
from crypt4gh.keys import get_private_key, get_public_key

from tests_ekss.fixtures.envelope import (
    EnvelopeFixture,
    envelope_fixture,  # noqa: F401
)
from tests_ekss.fixtures.utils import get_test_client
from tests_ekss.fixtures.vault import vault_fixture  # noqa: F401

pytestmark = pytest.mark.asyncio()


async def test_get_envelope(
    *,
    envelope_fixture: EnvelopeFixture,  # noqa: F811
):
    """Test request response for /secrets/../envelopes/.. endpoint with valid data"""
    secret_id = envelope_fixture.secret_id
    client_pk = base64.urlsafe_b64encode(
        get_public_key(envelope_fixture.public_key_path)
    ).decode("utf-8")
    client = get_test_client(envelope_fixture.config)
    response = client.get(url=f"/secrets/{secret_id}/envelopes/{client_pk}")
    assert response.status_code == 200
    body = response.json()
    content = base64.b64decode(body["content"])
    assert content
    client_sk = get_private_key(
        envelope_fixture.private_key_path,
        callback=lambda: envelope_fixture.config.private_key_passphrase,
    )
    keys = [(0, client_sk, None)]
    session_keys, _ = crypt4gh.header.deconstruct(
        infile=io.BytesIO(content),
        keys=keys,
        sender_pubkey=get_public_key(envelope_fixture.config.server_public_key_path),
    )
    assert session_keys[0] == envelope_fixture.secret


async def test_wrong_id(
    *,
    envelope_fixture: EnvelopeFixture,  # noqa: F811
):
    """Test request response for /secrets/../envelopes/.. endpoint with invalid secret_id"""
    secret_id = "wrong_id"
    client_pk = base64.urlsafe_b64encode(
        get_public_key(envelope_fixture.public_key_path)
    ).decode("utf-8")
    client = get_test_client(envelope_fixture.config)
    response = client.get(url=f"/secrets/{secret_id}/envelopes/{client_pk}")
    assert response.status_code == 404
    body = response.json()
    assert body["exception_id"] == "secretNotFoundError"
