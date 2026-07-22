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

"""Implementation of the LegacyResourceManager.

LEGACY: This component only exists to consume the "searchable resources" published by
the metldata producer (see rs.adapters.inbound.event_sub.ResourceSubTranslator).
Remove once this service owns studies and experimental metadata itself.
"""

import logging
from typing import Any
from uuid import UUID

import ghga_event_schemas.pydantic_ as event_schemas
from hexkit.protocols.dao import ResourceAlreadyExistsError
from pydantic import BaseModel, Field, ValidationError

from rs.core.models import Study, StudyStatus
from rs.ports.inbound.files import FileControllerPort
from rs.ports.inbound.legacy_resources import LegacyResourceManagerPort
from rs.ports.outbound.dao import StudyDao

log = logging.getLogger(__name__)

# The legacy searchable resources carry no information about who created a study or
# its lifecycle status. We therefore treat every ingested legacy study as ARCHIVED
# (these resources only ever represent published, immutable metadata) and attribute it
# to a sentinel "unknown" user. Both are placeholders until this service owns studies.
# The sentinel is an all-zero UUID with the version (4) and variant bits set so it
# validates as the UUID4 the Study model requires.
_LEGACY_STUDY_STATUS = StudyStatus.ARCHIVED
_LEGACY_CREATED_BY = UUID("00000000-0000-4000-8000-000000000000")


class _LegacyEmbeddedStudy(BaseModel):
    """The subset of the embedded study content we consume.

    Only the fields needed to build a Study are declared; any further properties
    carried by the payload are ignored (Pydantic's default for extra fields).
    """

    accession: str = Field(..., min_length=1)
    title: str
    description: str
    types: list[str]
    affiliations: list[str]
    # Only their lengths are consumed (as denormalized counters), so the element type
    # is irrelevant and they default to empty when absent from the payload.
    datasets: list[Any] = Field(default_factory=list)
    publications: list[Any] = Field(default_factory=list)


class _LegacyResourceContent(BaseModel):
    """The subset of a legacy searchable resource's content we consume.

    The ``files`` key carries the aggregation of all the resource's file accessions as
    a flat list of accession strings; it is the only source of tracked file accessions.
    Any further properties carried by the content are ignored.
    """

    study: _LegacyEmbeddedStudy
    files: list[str]


def _study_from_content(study: _LegacyEmbeddedStudy) -> Study:
    """Build a Study model from the legacy embedded study content.

    The denormalized counters are derived from the embedded lists; the status and
    creator are legacy placeholders (see module-level constants).
    """
    return Study(
        id=study.accession,
        title=study.title,
        description=study.description,
        types=study.types,
        affiliations=study.affiliations,
        status=_LEGACY_STUDY_STATUS,
        created_by=_LEGACY_CREATED_BY,
        num_datasets=len(study.datasets),
        num_publications=len(study.publications),
    )


class LegacyResourceManager(LegacyResourceManagerPort):
    """Handles searchable resources fetched from the metldata producer."""

    def __init__(
        self, *, study_dao: StudyDao, file_controller: FileControllerPort
    ) -> None:
        # The existing study DAO is injected to persist the studies extracted from the
        # consumed searchable resources. The file controller is used to track the file
        # accessions referenced by those resources.
        self._study_dao = study_dao
        self._file_controller = file_controller

    async def upsert_resource(
        self, *, resource: event_schemas.SearchableResource
    ) -> None:
        """Handle an upserted searchable resource.

        Legacy searchable resources (e.g. embedded datasets) carry the full study they
        belong to under the ``study`` key of their content, and the aggregation of all
        their file accessions under the ``files`` key. A resource that does not match
        this expected shape - no ``content`` mapping, a missing or null ``study``, a
        study without an ``accession``, or no ``files`` list - carries no usable
        metadata and is ignored with a warning.

        The embedded study is extracted and, if not already known, inserted via the
        study DAO. Studies are only ever created through this mechanism, never updated:
        the same
        study is typically embedded in many resources, and re-inserting it would
        needlessly reset its ``created`` timestamp and churn the outbox.

        In addition, we track every file accession referenced by the resource (under the
        ``files`` key) so that unmapped files become known before they are mapped to
        internal file IDs, associating each with the study.
        """
        try:
            parsed = _LegacyResourceContent.model_validate(resource.content)
        except ValidationError:
            log.warning(
                "Legacy searchable resource %s/%s does not match the expected schema"
                " (content with an embedded study carrying an accession and a files"
                " list), ignoring.",
                resource.class_name,
                resource.accession,
            )
            return

        study = _study_from_content(parsed.study)
        try:
            await self._study_dao.insert(study)
        except ResourceAlreadyExistsError:
            log.debug(
                "Study %s already exists, skipping legacy searchable resource %s/%s.",
                study.id,
                resource.class_name,
                resource.accession,
            )
        else:
            log.info(
                "Inserted study %s from legacy searchable resource %s/%s.",
                study.id,
                resource.class_name,
                resource.accession,
            )

        file_accessions = set(parsed.files)
        if file_accessions:
            await self._file_controller.register_unmapped_accessions(
                study_id=study.id, accessions=file_accessions
            )

    async def delete_resource(
        self, *, resource_info: event_schemas.SearchableResourceInfo
    ) -> None:
        """Handle a deleted searchable resource."""
        # TODO: Remove the corresponding Study from `self._study_dao` (idempotently).
        #   Until this service owns studies, we only observe the legacy deletion here.
        log.info(
            "Received legacy searchable resource deletion for %s/%s (not yet handled).",
            resource_info.class_name,
            resource_info.accession,
        )
