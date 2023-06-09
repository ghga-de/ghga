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

"""Event Models."""


from pydantic import BaseModel, Field

from metldata.custom_types import SubmissionContent
from metldata.submission_registry.models import AccessionMap


class SubmissionAnnotation(BaseModel):
    """Annotation on a given metadata submission."""

    accession_map: AccessionMap = Field(
        ...,
        description=(
            "A map of user-specified id to system-generated accession for metadata"
            + " resources. Keys on the top level correspond to names of metadata classes."
            + " Keys on the second level correspond to user-specified aliases."
            + " Values on the second level correspond to system-generated accessions."
            + " Please note that the user-defined alias might only be unique within"
            + " the scope of the corresponding class and this submission. By contrast,"
            + " the system-generated accession is unique across all classes and"
            + " submissions."
        ),
    )


class SubmissionEventPayload(BaseModel):
    """Model for an event payload."""

    submission_id: str
    content: SubmissionContent
    annotation: SubmissionAnnotation
