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
"""Top-level FastAPI router setup"""

from fastapi import APIRouter

from sms.adapters.inbound.fastapi_.routers.documents import mongodb_router
from sms.adapters.inbound.fastapi_.routers.events import kafka_router
from sms.adapters.inbound.fastapi_.routers.objects import s3_router

router = APIRouter(tags=["StateManagementService"])

router.include_router(mongodb_router, prefix="/documents", tags=["sms-mongodb"])
router.include_router(s3_router, prefix="/objects", tags=["sms-s3"])
router.include_router(kafka_router, prefix="/events", tags=["sms-kafka"])


@router.get(
    "/health",
    operation_id="health",
    summary="health",
    tags=["health"],
    status_code=200,
)
async def health():
    """Used to test if this service is alive"""
    return {"status": "OK"}
