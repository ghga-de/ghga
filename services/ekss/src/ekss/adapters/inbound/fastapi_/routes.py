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
"""Contains routes for encryption key store service operations"""

import base64
import logging
from typing import Annotated

from fastapi import APIRouter, Body, status

from ekss.adapters.inbound.fastapi_ import exceptions, models
from ekss.adapters.inbound.fastapi_.dummies import SecretsHandlerDummy
from ekss.constants import ENCODED_ENCRYPTED_KEY_SIZE, TRACER
from ekss.ports.inbound.secrets import SecretsHandlerPort

log = logging.getLogger(__name__)
router = APIRouter(tags=["EncryptionKeyStoreService"])

ERROR_RESPONSES = {
    "secretInsertionError": {
        "description": "Failed to successfully insert secret into vault.",
        "model": exceptions.HttpSecretInsertionError.get_body_model(),
    },
    "secretNotFoundError": {
        "description": "Could not find a secret for the given secret ID.",
        "model": exceptions.HttpSecretNotFoundError.get_body_model(),
    },
    "decodingError": {
        "description": (
            "One of the provided inputs could not be decoded as base64 string."
        ),
        "model": exceptions.HttpDecodingError.get_body_model(),
    },
    "decryptionError": {
        "description": "Could not decrypt the submitted file secret",
        "model": exceptions.HttpDecryptionError.get_body_model(),
    },
    "envelopeCreationError": {
        "description": "Could not create an envelope for the requested secret.",
        "model": exceptions.HttpEnvelopeCreationError.get_body_model(),
    },
    "secretDeletionError": {
        "description": "The secret was found but could not be deleted.",
        "model": exceptions.HttpSecretDeletionError.get_body_model(),
    },
    "internalError": {
        "description": "An internal server error has occurred.",
        "model": exceptions.HttpInternalError.get_body_model(),
    },
}


@router.get(
    "/health",
    summary="health",
    status_code=status.HTTP_200_OK,
)
@TRACER.start_as_current_span("routes.health")
async def health():
    """Used to test if this service is alive"""
    return {"status": "OK"}


@router.post(
    "/secrets",
    summary="Store Crypt4GH-encrypted file encryption secret",
    operation_id="postEncryptionData",
    status_code=status.HTTP_201_CREATED,
    response_model=models.SecretID,
    response_description="Successfully stored file encryption secret.",
    responses={
        status.HTTP_403_FORBIDDEN: ERROR_RESPONSES["decryptionError"],
        status.HTTP_422_UNPROCESSABLE_CONTENT: ERROR_RESPONSES["decodingError"],
        status.HTTP_500_INTERNAL_SERVER_ERROR: ERROR_RESPONSES["internalError"],
        status.HTTP_502_BAD_GATEWAY: ERROR_RESPONSES["secretInsertionError"],
    },
)
@TRACER.start_as_current_span("routes.post_encryption_secret")
async def post_encryption_secret(
    *,
    encrypted_secret: Annotated[
        str,
        Body(
            min_length=ENCODED_ENCRYPTED_KEY_SIZE,
            max_length=ENCODED_ENCRYPTED_KEY_SIZE,
            description=(
                "Base64-encoded string containing a Crypt4GH-encrypted file"
                + " encryption secret."
            ),
        ),
    ],
    secrets_handler: SecretsHandlerDummy,
):
    """Decrypt the provided Crypt4GH-encrypted file secret and store it in the key manager"""
    try:
        secret_id = secrets_handler.deposit_secret(encrypted_secret=encrypted_secret)
    except SecretsHandlerPort.SecretDecodeError as error:
        raise exceptions.HttpDecodingError(affected="decrypted secret") from error
    except SecretsHandlerPort.SecretDecryptionError as error:
        raise exceptions.HttpDecryptionError() from error
    except SecretsHandlerPort.SecretInsertionError as error:
        raise exceptions.HttpSecretInsertionError() from error
    except Exception as exc:
        log.error(str(exc), exc_info=True)
        raise exceptions.HttpInternalError(message="Failed to deposit secret") from exc

    return {"secret_id": secret_id}


@router.get(
    "/secrets/{secret_id}/envelopes/{client_pk}",
    summary="Get personalized envelope containing Crypt4GH file encryption/decryption key",
    operation_id="getEncryptionData",
    status_code=status.HTTP_200_OK,
    response_model=models.OutboundEnvelopeContent,
    response_description="Created personalized Crypt4GH envelope.",
    responses={
        status.HTTP_404_NOT_FOUND: ERROR_RESPONSES["secretNotFoundError"],
        status.HTTP_422_UNPROCESSABLE_CONTENT: ERROR_RESPONSES["decodingError"],
        status.HTTP_500_INTERNAL_SERVER_ERROR: ERROR_RESPONSES["envelopeCreationError"],
    },
)
@TRACER.start_as_current_span("routes.get_header_envelope")
async def get_header_envelope(
    *,
    secret_id: str,
    client_pk: str,
    secrets_handler: SecretsHandlerDummy,
):
    """Create header envelope for the file secret with given ID encrypted with a given public key"""
    try:
        client_pubkey = base64.urlsafe_b64decode(client_pk)
    except Exception as error:
        raise exceptions.HttpDecodingError(affected="client public key") from error
    try:
        header_envelope = secrets_handler.get_envelope(
            secret_id=secret_id,
            client_pubkey=client_pubkey,
        )
    except SecretsHandlerPort.SecretRetrievalError as error:
        raise exceptions.HttpSecretNotFoundError() from error
    except SecretsHandlerPort.EnvelopeCreationError as error:
        raise exceptions.HttpEnvelopeCreationError() from error
    except Exception as exc:
        log.error(str(exc), exc_info=True)
        message = f"Failed to get envelope for secret ID {secret_id}"
        raise exceptions.HttpInternalError(message=message) from exc

    return {
        "content": base64.b64encode(header_envelope).decode("utf-8"),
    }


@router.delete(
    "/secrets/{secret_id}",
    summary="Delete the associated secret",
    operation_id="deleteSecret",
    status_code=status.HTTP_204_NO_CONTENT,
    response_description="Successfully deleted secret.",
    responses={
        status.HTTP_404_NOT_FOUND: ERROR_RESPONSES["secretNotFoundError"],
        status.HTTP_500_INTERNAL_SERVER_ERROR: ERROR_RESPONSES["secretDeletionError"],
    },
)
@TRACER.start_as_current_span("routes.delete_secret")
async def delete_secret(
    *,
    secret_id: str,
    secrets_handler: SecretsHandlerDummy,
):
    """Delete the secret with the given ID from the key manager"""
    try:
        secrets_handler.delete_secret(secret_id=secret_id)
    except SecretsHandlerPort.SecretRetrievalError as error:
        raise exceptions.HttpSecretNotFoundError() from error
    except SecretsHandlerPort.SecretDeletionError as error:
        raise exceptions.HttpSecretDeletionError() from error
    except Exception as exc:
        log.error(str(exc), exc_info=True)
        message = f"Failed to delete secret with ID {secret_id}"
        raise exceptions.HttpInternalError(message=message) from exc
