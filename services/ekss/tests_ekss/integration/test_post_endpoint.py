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
"""Checking if POST on /secrets works correctly"""

import base64
import io

import crypt4gh.header
import pytest
from crypt4gh.keys import get_private_key

from tests_ekss.fixtures.file import (
    FirstPartFixture,
    first_part_fixture,  # noqa: F401
)
from tests_ekss.fixtures.utils import get_test_client
from tests_ekss.fixtures.vault import vault_fixture  # noqa: F401

pytestmark = pytest.mark.asyncio()


async def test_post_secrets(
    *,
    first_part_fixture: FirstPartFixture,  # noqa: F811
):
    """Test request response for /secrets endpoint with valid data"""
    payload = first_part_fixture.content

    request_body = {
        "public_key": base64.b64encode(first_part_fixture.client_pubkey).decode(
            "utf-8"
        ),
        "file_part": base64.b64encode(payload).decode("utf-8"),
    }
    client = get_test_client(first_part_fixture.config)
    response = client.post(url="/secrets", json=request_body)
    assert response.status_code == 200
    body = response.json()
    submitter_secret = base64.b64decode(body["submitter_secret"])

    config = first_part_fixture.config
    server_private_key = get_private_key(
        config.server_private_key_path, callback=lambda: config.private_key_passphrase
    )
    # (method - only 0 supported for now, private_key, public_key)
    keys = [(0, server_private_key, None)]
    session_keys, _ = crypt4gh.header.deconstruct(
        io.BytesIO(payload), keys, sender_pubkey=first_part_fixture.client_pubkey
    )

    assert submitter_secret == session_keys[0]
    assert body["new_secret"]
    assert body["secret_id"]
    assert body["offset"] > 0


async def test_corrupted_header(
    *,
    first_part_fixture: FirstPartFixture,  # noqa: F811
):
    """Test request response for /secrets endpoint with first char replaced in envelope"""
    payload = b"k" + first_part_fixture.content[2:]
    content = base64.b64encode(payload).decode("utf-8")

    request_body = {
        "public_key": base64.b64encode(first_part_fixture.client_pubkey).decode(
            "utf-8"
        ),
        "file_part": content,
    }

    client = get_test_client(first_part_fixture.config)
    response = client.post(url="/secrets", json=request_body)
    assert response.status_code == 400
    body = response.json()
    assert body["exception_id"] == "malformedOrMissingEnvelopeError"


async def test_invalid_pubkey(
    *,
    first_part_fixture: FirstPartFixture,  # noqa: F811
):
    """Test request response for /secrets endpoint with an invalid public key"""
    payload = first_part_fixture.content
    content = base64.b64encode(payload).decode("utf-8")

    request_body = {
        "public_key": "abc",
        "file_part": content,
    }

    client = get_test_client(first_part_fixture.config)
    response = client.post(url="/secrets", json=request_body)
    assert response.status_code == 422
    body = response.json()
    assert body["exception_id"] == "decodingError"


async def test_missing_envelope(
    *,
    first_part_fixture: FirstPartFixture,  # noqa: F811
):
    """Test request response for /secrets endpoint without envelope"""
    payload = first_part_fixture.content
    content = base64.b64encode(payload).decode("utf-8")
    content = content[124:]

    request_body = {
        "public_key": base64.b64encode(first_part_fixture.client_pubkey).decode(
            "utf-8"
        ),
        "file_part": content,
    }

    client = get_test_client(first_part_fixture.config)
    response = client.post(url="/secrets", json=request_body)
    assert response.status_code == 400
    body = response.json()
    assert body["exception_id"] == "malformedOrMissingEnvelopeError"


async def test_non_base64_envelope(
    *,
    first_part_fixture: FirstPartFixture,  # noqa: F811
):
    """Test request response for /secrets endpoint with malformed envelope"""
    payload = first_part_fixture.content
    content = "abc" + base64.b64encode(payload).decode("utf-8")

    request_body = {
        "public_key": base64.b64encode(first_part_fixture.client_pubkey).decode(
            "utf-8"
        ),
        "file_part": content,
    }

    client = get_test_client(first_part_fixture.config)
    response = client.post(url="/secrets", json=request_body)
    assert response.status_code == 422
    body = response.json()
    assert body["exception_id"] == "decodingError"
