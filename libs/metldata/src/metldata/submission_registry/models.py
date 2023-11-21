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
#

"""Data models"""

from enum import Enum
from operator import attrgetter
from typing import Optional

from ghga_service_commons.utils.utc_dates import DateTimeUTC, now_as_utc
from pydantic import BaseModel, Field, field_validator
from typing_extensions import TypeAlias

from metldata.custom_types import SubmissionContent

AccessionMap: TypeAlias = dict[str, dict[str, str]]


class SubmissionStatus(Enum):
    """Statuses a submission may have."""

    PENDING = "pending"
    IN_REVIEW = "in-review"
    CANCELED = "canceled"
    COMPLETED = "completed"
    DEPRECATED_PREPUBLICATION = "deprecated-prepublication"
    EMPTIED_PREPUBLICATION = "emptied-prepublication"
    PUBLISHED = "published"
    DEPRECATED_POSTPUBLICATION = "deprecated-postpublication"
    HIDDEN_POSTPUBLICATION = "hidden-postpublication"
    EMPTIED_POSTPUBLICATION = "emptied-postpublication"


class StatusChange(BaseModel):
    """A model for describing status changes of submissions."""

    timestamp: DateTimeUTC
    new_status: SubmissionStatus


class SubmissionHeader(BaseModel):
    """Basic information provided for a submission."""

    title: str = Field(..., description="A descriptive title for this submission.")
    description: Optional[str] = Field(None, description="An optional description.")


class Submission(SubmissionHeader):
    """A model for describing a submission."""

    id: str

    content: Optional[SubmissionContent] = Field(
        None,
        description=(
            "The metadata content of the submission. Keys on the top level correspond to"
            + " names of anchored metadata classes. Keys and values on the second level"
            + " correspond to the user-defined aliases and contents of class instance. Please note,"
            + " that the user-defined alias might only be unique within the scope of"
            + " the coressponding class and this submission."
        ),
    )

    accession_map: AccessionMap = Field(
        default_factory=dict,
        description=(
            "A map of user-specified id to system-generated accession for metadata"
            + " resources. Keys on the top level correspond to names of metadata classes."
            + " Keys on the second level correspond to user-specified aliases."
            + " Values on the second level correspond to system-generated accessions."
            + " Please note, that the user-defined alias might only be unique within"
            + " the scope of the coressponding class and this submission. By contrast,"
            + " the system-generated accession is unique across all classes and"
            + " submissions."
        ),
    )

    status_history: tuple[StatusChange, ...] = Field(
        default_factory=lambda: (
            StatusChange(timestamp=now_as_utc(), new_status=SubmissionStatus.PENDING),
        ),
        description="A history of status changes.",
    )

    @property
    def current_status(self) -> SubmissionStatus:
        """Extract the current submission status from the status history."""
        if len(self.status_history) == 0:
            raise RuntimeError("Status history is empty.")

        sorted_history = sorted(self.status_history, key=attrgetter("timestamp"))

        return sorted_history[-1].new_status

    @field_validator("accession_map")
    def check_accession_uniqueness(cls, value: AccessionMap) -> AccessionMap:
        """Check that no accessions are re-used accross classes."""
        total_resources = 0
        all_accessions: set[str] = set()

        for resources in value.values():
            total_resources += len(resources)
            all_accessions.update(resources.values())

        if len(all_accessions) != total_resources:
            raise ValueError("Accessions are not unique.")

        return value
