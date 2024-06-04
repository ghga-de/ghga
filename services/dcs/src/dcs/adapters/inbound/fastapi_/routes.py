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
"""Module containing the main FastAPI router and all route functions."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from dcs.adapters.inbound.fastapi_ import (
    dummies,
    http_authorization,
    http_exceptions,
    http_response_models,
    http_responses,
)
from dcs.core.auth_policies import WorkOrderContext
from dcs.core.models import DrsObjectResponseModel
from dcs.ports.inbound.data_repository import DataRepositoryPort

router = APIRouter()


RESPONSES = {
    "internalServerError": {
        "description": (
            "A configuration or external communication error has occurred and details "
            + "should not be communicated to the client"
        ),
        "model": http_exceptions.HttpInternalServerError.get_body_model(),
    },
    "noSuchObject": {
        "description": (
            "Exceptions by ID:\n- noSuchObject: The requested DrsObject was not found"
        ),
        "model": http_exceptions.HttpObjectNotFoundError.get_body_model(),
    },
    "objectNotInOutbox": {
        "description": (
            "The operation is delayed and will continue asynchronously. "
            + "The client should retry this same request after the delay "
            + "specified by Retry-After header."
        ),
        "model": http_response_models.DeliveryDelayedModel,
    },
    "wrongFileAuthorizationError": {
        "description": (
            "Work order token announced wrong file ID."
            + "\nExceptions by ID:"
            + "\n- wrongFileAuthorizationError: Mismatch of URL file ID and token file ID"
        ),
        "model": http_exceptions.HttpWrongFileAuthorizationError.get_body_model(),
    },
}


@router.get(
    "/health",
    summary="health",
    tags=["DownloadControllerService"],
    status_code=status.HTTP_200_OK,
)
async def health():
    """Used to test if this service is alive"""
    return {"status": "OK"}


@router.get(
    "/objects/{object_id}",
    summary="Returns object metadata, and a list of access methods that can be used "
    + "to fetch object bytes.",
    operation_id="getDrsObject",
    tags=["DownloadControllerService"],
    status_code=status.HTTP_200_OK,
    response_model=DrsObjectResponseModel,
    response_description="The DrsObject was found successfully.",
    responses={
        status.HTTP_202_ACCEPTED: RESPONSES["objectNotInOutbox"],
        status.HTTP_403_FORBIDDEN: RESPONSES["wrongFileAuthorizationError"],
        status.HTTP_404_NOT_FOUND: RESPONSES["noSuchObject"],
        status.HTTP_500_INTERNAL_SERVER_ERROR: RESPONSES["internalServerError"],
    },
)
async def get_drs_object(
    object_id: str,
    data_repository: Annotated[DataRepositoryPort, Depends(dummies.data_repo_port)],
    work_order_context: Annotated[
        WorkOrderContext, http_authorization.require_work_order_context
    ],
):
    """
    Get info about a ``DrsObject``. The object_id parameter refers to the file id
    and **not** the S3 object id.
    """
    if not work_order_context.file_id == object_id:
        raise http_exceptions.HttpWrongFileAuthorizationError()

    try:
        drs_object = await data_repository.access_drs_object(drs_id=object_id)
        return drs_object

    except data_repository.RetryAccessLaterError as retry_later_error:
        # tell client to retry after 5 minutes
        return http_responses.HttpObjectNotInOutboxResponse(
            retry_after=retry_later_error.retry_after
        )

    except data_repository.DrsObjectNotFoundError as object_not_found_error:
        raise http_exceptions.HttpObjectNotFoundError(
            object_id=object_id
        ) from object_not_found_error

    except data_repository.StorageAliasNotConfiguredError as configuration_error:
        raise http_exceptions.HttpInternalServerError() from configuration_error


@router.get(
    "/objects/{object_id}/envelopes",
    summary="Returns base64 encoded, personalized file envelope",
    operation_id="getEnvelope",
    tags=["DownloadControllerService"],
    status_code=status.HTTP_200_OK,
    response_model=http_response_models.EnvelopeResponseModel,
    response_description="Successfully delivered envelope.",
    responses={
        status.HTTP_403_FORBIDDEN: RESPONSES["wrongFileAuthorizationError"],
        status.HTTP_404_NOT_FOUND: RESPONSES["noSuchObject"],
        status.HTTP_500_INTERNAL_SERVER_ERROR: RESPONSES["internalServerError"],
    },
)
async def get_envelope(
    object_id: str,
    work_order_context: Annotated[
        WorkOrderContext, http_authorization.require_work_order_context
    ],
    data_repository: Annotated[DataRepositoryPort, Depends(dummies.data_repo_port)],
):
    """
    Retrieve the base64 encoded envelope for a given object based on object id and
    URL safe base64 encoded public key. The object_id parameter refers to the file id
    and **not** the S3 object id.
    """
    if not work_order_context.file_id == object_id:
        raise http_exceptions.HttpWrongFileAuthorizationError()

    public_key = work_order_context.user_public_crypt4gh_key

    try:
        envelope = await data_repository.serve_envelope(
            drs_id=object_id, public_key=public_key
        )
    except data_repository.DrsObjectNotFoundError as object_not_found_error:
        raise http_exceptions.HttpObjectNotFoundError(
            object_id=object_id
        ) from object_not_found_error
    except (
        data_repository.APICommunicationError,
        data_repository.EnvelopeNotFoundError,
    ) as communication_error:
        raise http_exceptions.HttpInternalServerError() from communication_error

    return http_responses.HttpEnvelopeResponse(envelope=envelope)
