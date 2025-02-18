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

"""Reusable HTTP response definitions"""

from uuid import UUID

from fastapi import status
from ghga_service_commons.httpyexpect.server.exceptions import HttpCustomExceptionBase

from dlqs.models import EventCore


class HttpInternalServerError(HttpCustomExceptionBase):
    """Thrown when an error is raised with details that should not be propagated to a client"""

    exception_id = "internalServerError"

    def __init__(self, *, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code, description="Internal Server Error.", data={}
        )


class HttpPreviewParamsError(HttpCustomExceptionBase):
    """Thrown when an error is raised because of invalid values for `skip` or `limit`"""

    exception_id = "previewParamsError"

    def __init__(
        self,
        *,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        skip: int,
        limit: int | None,
    ):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description=(
                "Invalid values for `skip` and/or `limit`. Skip must be >=0 if supplied"
                + " and limit must be >=1 if supplied."
            ),
            data={"skip": skip, "limit": limit},
        )


class HttpOverrideValidationError(HttpCustomExceptionBase):
    """Thrown when a manually supplied override event does not pass validation"""

    exception_id = "overrideValidationError"

    def __init__(
        self,
        *,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        event: EventCore | None,
        reason: str,
    ):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description="Event validation failed.",
            data={"event": event.model_dump() if event else {}, "reason": reason},
        )


class HttpEmptyDLQError(HttpCustomExceptionBase):
    """Thrown when trying to process with an empty DLQ"""

    exception_id = "emptyDLQError"

    def __init__(
        self,
        *,
        status_code: int = status.HTTP_404_NOT_FOUND,
        service: str,
        topic: str,
    ):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description="No DLQ events exist for the given service and topic.",
            data={"service": service, "topic": topic},
        )


class HttpSequenceError(HttpCustomExceptionBase):
    """Thrown when the supplied DLQ ID doesn't match that of the next event in the DLQ"""

    exception_id = "dlqSequenceError"

    def __init__(
        self,
        *,
        status_code: int = status.HTTP_409_CONFLICT,
        service: str,
        topic: str,
        dlq_id: UUID,
    ):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description="The supplied DLQ ID does not match the next event in the DLQ.",
            data={"service": service, "topic": topic, "supplied_dlq_id": str(dlq_id)},
        )
