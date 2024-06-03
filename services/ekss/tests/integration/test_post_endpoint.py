# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
"""Checking if POST on /secrets works correctly"""

import base64
import io

import crypt4gh.header
import pytest
from fastapi.testclient import TestClient

from ekss.adapters.inbound.fastapi_.deps import config_injector
from ekss.adapters.inbound.fastapi_.main import setup_app
from ekss.config import CONFIG
from tests.fixtures.file import (
    FirstPartFixture,
    first_part_fixture,  # noqa: F401
)
from tests.fixtures.keypair import generate_keypair_fixture  # noqa: F401
from tests.fixtures.vault import vault_fixture  # noqa: F401

app = setup_app(CONFIG)
client = TestClient(app=app)


@pytest.mark.asyncio
async def test_post_secrets(
    *,
    first_part_fixture: FirstPartFixture,  # noqa: F811
):
    """Test request response for /secrets endpoint with valid data"""
    app.dependency_overrides[config_injector] = lambda: first_part_fixture.vault.config

    payload = first_part_fixture.content

    request_body = {
        "public_key": base64.b64encode(first_part_fixture.client_pubkey).decode(
            "utf-8"
        ),
        "file_part": base64.b64encode(payload).decode("utf-8"),
    }

    response = client.post(url="/secrets", json=request_body)
    assert response.status_code == 200
    body = response.json()
    submitter_secret = base64.b64decode(body["submitter_secret"])

    server_private_key = base64.b64decode(CONFIG.server_private_key.get_secret_value())
    # (method - only 0 supported for now, private_key, public_key)
    keys = [(0, server_private_key, None)]
    session_keys, _ = crypt4gh.header.deconstruct(
        io.BytesIO(payload), keys, sender_pubkey=first_part_fixture.client_pubkey
    )

    assert submitter_secret == session_keys[0]
    assert body["new_secret"]
    assert body["secret_id"]
    assert body["offset"] > 0


@pytest.mark.asyncio
async def test_corrupted_header(
    *,
    first_part_fixture: FirstPartFixture,  # noqa: F811
):
    """Test request response for /secrets endpoint with first char replaced in envelope"""
    app.dependency_overrides[config_injector] = lambda: first_part_fixture.vault.config

    payload = b"k" + first_part_fixture.content[2:]
    content = base64.b64encode(payload).decode("utf-8")

    request_body = {
        "public_key": base64.b64encode(first_part_fixture.client_pubkey).decode(
            "utf-8"
        ),
        "file_part": content,
    }

    response = client.post(url="/secrets", json=request_body)
    assert response.status_code == 400
    body = response.json()
    assert body["exception_id"] == "malformedOrMissingEnvelopeError"


@pytest.mark.asyncio
async def test_missing_envelope(
    *,
    first_part_fixture: FirstPartFixture,  # noqa: F811
):
    """Test request response for /secrets endpoint without envelope"""
    app.dependency_overrides[config_injector] = lambda: first_part_fixture.vault.config

    payload = first_part_fixture.content
    content = base64.b64encode(payload).decode("utf-8")
    content = content[124:]

    request_body = {
        "public_key": base64.b64encode(first_part_fixture.client_pubkey).decode(
            "utf-8"
        ),
        "file_part": content,
    }

    response = client.post(url="/secrets", json=request_body)
    assert response.status_code == 400
    body = response.json()
    assert body["exception_id"] == "malformedOrMissingEnvelopeError"
