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
"""FastAPI routes for S3 upload metadata ingest"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import JSONResponse

from fis.adapters.inbound.fastapi_ import dummies
from fis.adapters.inbound.fastapi_.http_authorization import (
    IngestTokenAuthContext,
    require_token,
)
from fis.core.models import EncryptedPayload, UploadMetadata
from fis.ports.inbound.ingest import (
    DecryptionError,
    VaultCommunicationError,
    WrongDecryptedFormatError,
)

router = APIRouter()


@router.get(
    "/health",
    summary="health",
    tags=["FileIngestService"],
    status_code=200,
)
async def health():
    """Used to test if this service is alive"""
    return {"status": "OK"}


@router.post(
    "/legacy/ingest",
    summary="Processes encrypted output data from the S3 upload script and ingests it "
    + "into the Encryption Key Store, Internal File Registry and Download Controller.",
    operation_id="ingestLegacyFileUploadMetadata",
    tags=["FileIngestService"],
    status_code=status.HTTP_202_ACCEPTED,
    response_description="Received and decrypted data successfully.",
    deprecated=True,
    responses={
        status.HTTP_409_CONFLICT: {
            "description": "Metadata for the given file ID has already been processed."
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": "Either the payload is malformed or could not be decrypted.",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/HTTPValidationError"}
                }
            },
        },
    },
)
async def ingest_legacy_metadata(
    encrypted_payload: EncryptedPayload,
    upload_metadata_processor: dummies.LegacyUploadProcessor,
    _token: Annotated[IngestTokenAuthContext, require_token],
):
    """Decrypt payload, process metadata, file secret and send success event"""
    try:
        decrypted_metadata = await upload_metadata_processor.decrypt_payload(
            encrypted=encrypted_payload
        )
    except (DecryptionError, WrongDecryptedFormatError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    file_id = decrypted_metadata.file_id
    if await upload_metadata_processor.has_already_been_processed(file_id=file_id):
        return JSONResponse(
            status_code=409,
            content={
                "error": f"Metadata for file {file_id} has already been processed."
            },
        )

    file_secret = decrypted_metadata.file_secret

    try:
        secret_id = await upload_metadata_processor.store_secret(
            file_secret=file_secret
        )
    except VaultCommunicationError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    await upload_metadata_processor.populate_by_event(
        upload_metadata=decrypted_metadata, secret_id=secret_id
    )

    return Response(status_code=202)


@router.post(
    "/federated/ingest_metadata",
    summary="Processes encrypted output data from the S3 upload script and ingests it "
    + "into the Encryption Key Store, Internal File Registry and Download Controller.",
    operation_id="ingestFileUploadMetadata",
    tags=["FileIngestService"],
    status_code=status.HTTP_202_ACCEPTED,
    response_description="Received and decrypted data successfully.",
    responses={
        status.HTTP_409_CONFLICT: {
            "description": "Metadata for the given file ID has already been processed."
        }
    },
)
async def ingest_metadata(
    payload: UploadMetadata,
    upload_metadata_processor: dummies.UploadProcessorPort,
    _token: Annotated[IngestTokenAuthContext, require_token],
):
    """Process metadata, file secret id and send success event"""
    secret_id = payload.secret_id
    file_id = payload.file_id
    if await upload_metadata_processor.has_already_been_processed(file_id=file_id):
        return JSONResponse(
            status_code=409,
            content={
                "error": f"Metadata for file {file_id} has already been processed."
            },
        )

    await upload_metadata_processor.populate_by_event(
        upload_metadata=payload, secret_id=secret_id
    )

    return Response(status_code=202)


@router.post(
    "/federated/ingest_secret",
    summary="Store file encryption/decryption secret and return secret ID.",
    operation_id="ingestSecret",
    tags=["FileIngestService"],
    status_code=status.HTTP_200_OK,
    response_description="Received and stored secret successfully.",
    responses={
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": "Either the payload is malformed or could not be decrypted.",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/HTTPValidationError"}
                }
            },
        },
    },
)
async def ingest_secret(
    encrypted_payload: EncryptedPayload,
    upload_metadata_processor: dummies.UploadProcessorPort,
    _token: Annotated[IngestTokenAuthContext, require_token],
):
    """Decrypt payload and deposit file secret in exchange for a secret id"""
    try:
        file_secret = await upload_metadata_processor.decrypt_secret(
            encrypted=encrypted_payload
        )
    except DecryptionError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    secret_id = await upload_metadata_processor.store_secret(file_secret=file_secret)
    return {"secret_id": secret_id}
