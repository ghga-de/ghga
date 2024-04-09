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
"""Module containing the main FastAPI router and all route functions."""

from typing import Annotated

from fastapi import APIRouter, status

from pcs.adapters.inbound.fastapi_ import dummies
from pcs.adapters.inbound.fastapi_.http_authorization import (
    TokenAuthContext,
    require_token,
)

router = APIRouter()


@router.get(
    "/health",
    summary="health",
    tags=["PurgeControllerService"],
    status_code=status.HTTP_200_OK,
)
async def health():
    """Used to test if this service is alive"""
    return {"status": "OK"}


@router.delete(
    "/files/{file_id}",
    summary="Deletes the corresponding file.",
    operation_id="deleteFile",
    tags=["PurgeControllerService"],
    status_code=status.HTTP_202_ACCEPTED,
    response_description="Commissioned file deletion",
)
async def delete_file(
    file_id: str,
    file_deletion: dummies.FileDeletionDummy,
    _token: Annotated[TokenAuthContext, require_token],
):
    """Send out an event to delete the file with the given id."""
    # Perform file deletion
    await file_deletion.delete_file(file_id=file_id)

    return status.HTTP_202_ACCEPTED
