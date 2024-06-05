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
"""Mock EKSS endpoints"""

import httpx
from fastapi import status
from ghga_service_commons.api.mock_router import MockRouter
from ghga_service_commons.httpyexpect.server.exceptions import (
    HttpCustomExceptionBase,
    HttpException,
)


class HttpSecretNotFoundError(HttpCustomExceptionBase):
    """Thrown when no secret with the given id could be found"""

    exception_id = "secretNotFoundError"

    def __init__(self, *, status_code: int = 404):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description="The secret for the given id was not found.",
            data={},
        )


def httpy_exception_handler(request: httpx.Request, exc: HttpException):
    """Transform HttpException data into a proper response object"""
    return httpx.Response(
        status_code=exc.status_code,
        json={
            "exception_id": exc.body.exception_id,
            "description": exc.body.description,
            "data": exc.body.data,
        },
    )


router = MockRouter(httpy_exception_handler)


@router.get(
    "/secrets/{secret_id}/envelopes/{receiver_public_key}",
)
def ekss_get_envelope_mock(secret_id: str, receiver_public_key: str):
    """Mock API call to the EKSS to get the envelope"""
    valid_secret = "some-secret"

    if secret_id != valid_secret:
        raise HttpSecretNotFoundError()

    envelope = (
        "pfAcB7o2lz0075VTpb6b5PCdfWnPofyZ62RYxQ6gZflUoCuwSt//R2N6QCWTnn7wV/oU8syQBCgB/1KTqz77v"
        + "8jBF73IyszJzVezDokPe8AJIEFG18luo/ZRI9mDSEI/GFy2EtNdflqW+CBSgUEWiQjkRAwS3V+dVeFsVQ=="
    )

    return httpx.Response(status_code=status.HTTP_200_OK, json={"content": envelope})


@router.delete("/secrets/{secret_id}")
def ekss_delete_secret_mock(secret_id: str):
    """Mock API call to the EKSS to delete file secret"""
    valid_secret = "some-secret"

    if secret_id != valid_secret:
        raise HttpSecretNotFoundError()

    return httpx.Response(status_code=status.HTTP_204_NO_CONTENT)
