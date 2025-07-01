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

from fastapi import APIRouter, Response, status
from ghga_service_commons.httpyexpect.server.exceptions import HttpCustomExceptionBase

from rts.adapters.inbound.fastapi_.dummies import ReverseTranspilerDummy

router = APIRouter()

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class HttpMetadataNotFoundError(HttpCustomExceptionBase):
    """Thrown when metadata for a study accession is not found."""

    exception_id = "metadataNotFoundError"

    def __init__(self, study_accession: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            description="Metadata for study accession not found.",
            data={"study_accession": study_accession},
        )


@router.get(
    "/health",
    summary="health",
    status_code=status.HTTP_200_OK,
)
async def health():
    """Used to test if this service is alive"""
    return {"status": "OK"}


# TODO: Fill in endpoint metadata and check type-hinting
@router.get(
    "/studies/{accession}",
    summary="Get accessioned metadata in .xlsx format",
    status_code=status.HTTP_200_OK,
)
async def get_transpiled_metadata(
    accession: str,
    reverse_transpiler: ReverseTranspilerDummy,
) -> Response:
    """Get a transpiled metadata file for a specific artifact, class, and resource."""
    try:
        data = await reverse_transpiler.retrieve_workbook(study_accession=accession)
    except reverse_transpiler.MetadataNotFoundError as err:
        raise HttpMetadataNotFoundError(study_accession=accession) from err

    response = Response(
        status_code=200,
        content=data,
        headers={
            "Content-Disposition": f'attachment; filename="{accession}.xlsx"',
            "Content-Type": XLSX_CONTENT_TYPE,
        },
    )
    return response
