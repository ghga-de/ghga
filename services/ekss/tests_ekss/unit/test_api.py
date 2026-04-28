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

"""Testing the basics of the service API"""

import base64
import os

import pytest

from ekss.ports.inbound.secrets import SecretsHandlerPort
from tests_ekss.fixtures.client import ClientFixture
from tests_ekss.fixtures.keypair import KeypairFixture
from tests_ekss.fixtures.utils import make_secret_payload

pytestmark = pytest.mark.asyncio


async def test_health_check(client_fixture: ClientFixture):
    """Test that the health check endpoint works."""
    response = await client_fixture.client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "OK"}


async def test_get_envelope(client_fixture: ClientFixture, keypair: KeypairFixture):
    """Test the GET /secrets/{secret_id}/envelopes/{client_pk} endpoint"""
    fake_envelope = os.urandom(64)
    client_fixture.secrets_handler.get_envelope.return_value = fake_envelope

    encoded_pk = base64.urlsafe_b64encode(keypair.user_pk).decode("utf-8")
    response = await client_fixture.client.get(
        f"/secrets/test-secret-id/envelopes/{encoded_pk}"
    )

    assert response.status_code == 200
    assert response.json() == {
        "content": base64.b64encode(fake_envelope).decode("utf-8")
    }


async def test_post_secret(client_fixture: ClientFixture, keypair: KeypairFixture):
    """Test the POST /secrets endpoint (no core errors)"""
    # Should get an error when body is empty
    response = await client_fixture.client.post("/secrets")
    assert response.status_code == 422

    response = await client_fixture.client.post("/secrets", content=b"")
    assert response.status_code == 422

    response = await client_fixture.client.post("/secrets", content=b"a" * 123)
    assert response.status_code == 422

    response = await client_fixture.client.post("/secrets", content=b"a" * 125)
    assert response.status_code == 422

    # Now for success case - Generate a secret to submit
    _, encrypted_secret = make_secret_payload(keypair.ekss_pk)

    # Fix the return value for the secrets handler
    client_fixture.secrets_handler.deposit_secret.return_value = "secret123"

    # Post secret and inspect response
    response = await client_fixture.client.post("/secrets", content=encrypted_secret)
    assert response.status_code == 201
    assert response.json() == {"secret_id": "secret123"}


async def test_delete_secret(client_fixture: ClientFixture):
    """Test that successful secret deletion results in a 204 status code"""
    response = await client_fixture.client.delete("/secrets/some-secret-id")
    assert response.status_code == 204


# The following error translation tests are broken out by endpoint for readability:


@pytest.mark.parametrize(
    "core_error, exception_id, status_code",
    [
        (
            SecretsHandlerPort.SecretRetrievalError(secret_id="test-id"),
            "secretNotFoundError",
            404,
        ),
        (
            SecretsHandlerPort.EnvelopeCreationError(secret_id="test-id"),
            "envelopeCreationError",
            500,
        ),
        (Exception("unexpected"), "internalError", 500),
    ],
)
async def test_error_translation_get_envelope(
    client_fixture: ClientFixture,
    core_error: type[Exception],
    exception_id: str,
    status_code: int,
):
    """Test that core errors are translated to the correct HTTP errors for the GET endpoint"""
    client_fixture.secrets_handler.get_envelope.side_effect = core_error
    response = await client_fixture.client.get(
        "/secrets/test-id/envelopes/dGVzdC1wdWJrZXk="
    )
    assert response.status_code == status_code
    assert response.json()["exception_id"] == exception_id


@pytest.mark.parametrize(
    "core_error, exception_id, status_code",
    [
        (SecretsHandlerPort.SecretDecryptionError(), "decryptionError", 403),
        (SecretsHandlerPort.SecretDecodeError(), "decodingError", 422),
        (SecretsHandlerPort.SecretInsertionError(), "secretInsertionError", 502),
        (Exception("unexpected"), "internalError", 500),
    ],
)
async def test_error_translation_post_secret(
    keypair: KeypairFixture,
    client_fixture: ClientFixture,
    core_error: type[Exception],
    exception_id: str,
    status_code: int,
):
    """Test that core errors are translated to the correct HTTP errors for the POST endpoint"""
    client_fixture.secrets_handler.deposit_secret.side_effect = core_error
    _, encrypted_secret = make_secret_payload(keypair.ekss_pk)
    response = await client_fixture.client.post("/secrets", content=encrypted_secret)
    assert response.status_code == status_code
    assert response.json()["exception_id"] == exception_id


@pytest.mark.parametrize(
    "core_error, exception_id, status_code",
    [
        (
            SecretsHandlerPort.SecretRetrievalError(secret_id="test-id"),
            "secretNotFoundError",
            404,
        ),
        (
            SecretsHandlerPort.SecretDeletionError(secret_id="test-id"),
            "secretDeletionError",
            500,
        ),
        (Exception("unexpected"), "internalError", 500),
    ],
)
async def test_error_translation_delete_secret(
    client_fixture: ClientFixture,
    core_error: type[Exception],
    exception_id: str,
    status_code: int,
):
    """Test that core errors are translated to the correct HTTP errors for the DELETE endpoint"""
    client_fixture.secrets_handler.delete_secret.side_effect = core_error
    response = await client_fixture.client.delete("/secrets/test-id")
    assert response.status_code == status_code
    assert response.json()["exception_id"] == exception_id
