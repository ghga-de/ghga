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

"""FastAPI endpoint function definitions"""

from fastapi import APIRouter, status

from rts.adapters.inbound.fastapi_.dummies import ReverseTranspilerDummy

router = APIRouter()


@router.get(
    "/health",
    summary="health",
    status_code=status.HTTP_200_OK,
)
async def health():
    """Used to test if this service is alive"""
    return {"status": "OK"}


# Make a GET endpoint that can serve a transpiled metadata file
@router.get(
    "/artifacts/{artifact_name}/classes/{class_name}/resources/{resource_id}",
    summary="Get transpiled metadata",
    status_code=status.HTTP_200_OK,
)
async def get_transpiled_metadata(
    artifact_name: str,
    class_name: str,
    resource_id: str,
    reverse_transpiler: ReverseTranspilerDummy,
):
    """Get a transpiled metadata file for a specific artifact, class, and resource."""
    raise NotImplementedError()
