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

"""General data model with build in validation."""

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

EXCEPTION_ID_PATTERN = r"^[a-z][a-zA-Z0-9]{2,39}$"


class HttpExceptionBody(BaseModel):
    """An opinionated base schema/model for the response body.

    Shipped with HTTP exception (on 4xx or 5xx status codes).
    """

    model_config = ConfigDict(extra="forbid")

    data: dict[str, Any] = Field(
        ...,
        description=(
            "An object containing further details on the exception cause in a"
            + " machine readable way. All exceptions with the same exception_id should"
            + " use the same set of properties here. This object may be empty (in case"
            + " no data is required)"
        ),
    )
    description: str = Field(
        ...,
        description=(
            "A human readable message to the client explaining the cause of the"
            + " exception."
        ),
    )
    exception_id: Annotated[
        str, StringConstraints(pattern=EXCEPTION_ID_PATTERN)
    ] = Field(
        ...,
        description=(
            "An identifier used to distinguish between different exception"
            + " causes in a preferably fine-grained fashion. The distinction between"
            + " causes should be made from the perspective of the server/service"
            + " raising the exception (and not from the client perspective). Needs to"
            + " be camel case formatted and 3-40 character in length."
        ),
    )
