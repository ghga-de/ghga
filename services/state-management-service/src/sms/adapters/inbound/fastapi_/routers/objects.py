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
"""FastAPI routes for S3 state management."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, status

from sms.adapters.inbound.fastapi_ import dummies
from sms.adapters.inbound.fastapi_.http_authorization import (
    TokenAuthContext,
    require_token,
)
from sms.ports.inbound.objects_handler import ObjectsHandlerPort, S3ObjectStoragesPort

s3_router = APIRouter()


@s3_router.get(
    "/{alias}/{bucket_id}/{object_id}",
    operation_id="check_object_exists",
    summary="Check if an object exists in the specified bucket.",
    status_code=status.HTTP_200_OK,
    response_model=bool,
)
async def does_object_exist(
    alias: str,
    bucket_id: str,
    object_id: str,
    objects_handler: dummies.ObjectsHandlerPortDummy,
    _token: Annotated[TokenAuthContext, require_token],
):
    """Return boolean indicating whether or not the object exists in the given bucket."""
    try:
        return await objects_handler.does_object_exist(
            alias=alias, bucket_id=bucket_id, object_id=object_id
        )
    except ObjectsHandlerPort.InvalidIdError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(err)
        ) from err
    except (
        S3ObjectStoragesPort.AliasNotConfiguredError,
        ObjectsHandlerPort.BucketNotFoundError,
    ) as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(err)
        ) from err
    except ObjectsHandlerPort.OperationError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err)
        ) from err


@s3_router.get(
    "/{alias}/{bucket_id}",
    operation_id="get_objects",
    summary="List all objects in the specified bucket.",
    status_code=status.HTTP_200_OK,
    response_model=list[str],
)
async def list_objects(
    alias: str,
    bucket_id: str,
    objects_handler: dummies.ObjectsHandlerPortDummy,
    _token: Annotated[TokenAuthContext, require_token],
):
    """Return a list of the objects that currently exist in the S3 bucket."""
    try:
        return await objects_handler.list_objects(alias=alias, bucket_id=bucket_id)
    except (
        S3ObjectStoragesPort.AliasNotConfiguredError,
        ObjectsHandlerPort.BucketNotFoundError,
    ) as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(err)
        ) from err
    except ObjectsHandlerPort.InvalidBucketIdError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(err)
        ) from err
    except ObjectsHandlerPort.OperationError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err)
        ) from err


@s3_router.delete(
    "/{alias}/{bucket_id}",
    operation_id="empty_bucket",
    summary="Delete all objects in the specified bucket.",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_objects(
    alias: str,
    bucket_id: str,
    objects_handler: dummies.ObjectsHandlerPortDummy,
    _token: Annotated[TokenAuthContext, require_token],
):
    """Delete all objects in the specified bucket."""
    try:
        await objects_handler.empty_bucket(alias=alias, bucket_id=bucket_id)
    except S3ObjectStoragesPort.AliasNotConfiguredError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(err)
        ) from err
    except ObjectsHandlerPort.InvalidBucketIdError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(err)
        ) from err
    except ObjectsHandlerPort.OperationError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err)
        ) from err
    except ObjectsHandlerPort.BucketNotFoundError:
        pass
