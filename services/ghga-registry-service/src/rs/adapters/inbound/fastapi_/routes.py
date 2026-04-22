# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""FastAPI endpoints for RS interaction"""

import logging

from fastapi import APIRouter

from rs.adapters.inbound.fastapi_.routers.upload_boxes import box_router
from rs.adapters.inbound.fastapi_.routers.upload_grants import upload_grant_router
from rs.constants import TRACER

log = logging.getLogger(__name__)

router = APIRouter()


router.include_router(
    box_router, prefix="/upload-boxes", tags=["ResearchDataUploadBoxes"]
)
router.include_router(
    upload_grant_router, prefix="/upload-grants", tags=["UploadGrants"]
)


@router.get(
    "/health",
    summary="health",
    status_code=200,
)
@TRACER.start_as_current_span("routes.health")
async def health():
    """Used to test if this service is alive"""
    return {"status": "OK"}


# TODO: Add `/filenames/{study_id}` endpoint to get ACCESSION -> name & alias mapping for files
