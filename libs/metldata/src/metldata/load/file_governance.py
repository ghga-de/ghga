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
#

"""Resolve the governance of every loaded file and store it by file accession."""

from typing import TypeAlias

from hexkit.protocols.dao import Dao, DaoFactoryProtocol
from metldata.artifacts_rest.models import ArtifactInfo
from metldata.governance import (
    GovernanceMetadata,
    GovernanceResolutionError,
    resolve_files_governance,
)
from metldata.load.load import ArtifactResourcesInvalid
from metldata.load.models import ArtifactResourceDict, FileGovernanceRecord
from metldata.metadata_utils import SelfIdLookUpError, lookup_self_id
from metldata.model_utils.essentials import is_file_class

FILE_GOVERNANCE_COLLECTION_NAME = "file_governance"

FileGovernanceDao: TypeAlias = Dao[FileGovernanceRecord]


async def get_file_governance_dao(
    *, dao_factory: DaoFactoryProtocol
) -> FileGovernanceDao:
    """Get the DAO for the file governance collection."""
    return await dao_factory.get_dao(
        name=FILE_GOVERNANCE_COLLECTION_NAME,
        dto_model=FileGovernanceRecord,
        id_field="file_accession",
    )


def resolve_governance_records(
    *,
    artifact_resources: ArtifactResourceDict,
    artifact_info_dict: dict[str, ArtifactInfo],
    governance_artifact_name: str,
) -> list[FileGovernanceRecord]:
    """Resolve the governance of every file in the governance artifacts.

    Each artifact is resolved on its own, querying its own file accessions. If no
    governance artifact is present, there are no files to govern. Call this after
    `check_artifact_resources`, which rejects artifacts without an artifact info.

    Raises:
        ArtifactResourcesInvalid: If a resource on the governance chain has no
            identifier, a reference on it is dangling, a file does not resolve to
            exactly one dataset, or a file accession occurs in more than one
            artifact.
    """
    artifacts = artifact_resources.get(governance_artifact_name, [])
    if not artifacts:
        return []

    anchor_points_by_target = {
        class_name: resource_class.anchor_point
        for class_name, resource_class in artifact_info_dict[
            governance_artifact_name
        ].resource_classes.items()
    }
    records_by_file_accession: dict[str, FileGovernanceRecord] = {}

    for artifact in artifacts:
        content = artifact["content"]
        try:
            file_accessions = [
                lookup_self_id(
                    resource=file, identifier_slot=anchor_point.identifier_slot
                )
                for class_name, anchor_point in anchor_points_by_target.items()
                if is_file_class(class_name)
                for file in content.get(anchor_point.root_slot, [])
            ]
            governance_by_file_accession = resolve_files_governance(
                file_accessions=file_accessions,
                metadata=GovernanceMetadata.from_artifacts(
                    contents=[content], anchor_points_by_target=anchor_points_by_target
                ),
            )
        except (GovernanceResolutionError, SelfIdLookUpError) as error:
            raise ArtifactResourcesInvalid(
                f"Artifact '{governance_artifact_name}' of study"
                + f" '{artifact['study_accession']}': {error}"
            ) from error

        for file_accession, governance in governance_by_file_accession.items():
            # A file of the same artifact that reuses this file's accession is
            # matched as well, which would leave the file with two governances:
            if len(governance) != 1:
                raise ArtifactResourcesInvalid(
                    f"File '{file_accession}' resolves to {len(governance)} datasets"
                    + " instead of exactly one."
                )
            if file_accession in records_by_file_accession:
                raise ArtifactResourcesInvalid(
                    f"File '{file_accession}' occurs in more than one artifact"
                    + f" '{governance_artifact_name}'."
                )
            records_by_file_accession[file_accession] = FileGovernanceRecord(
                file_accession=file_accession, **governance[0].model_dump()
            )

    return list(records_by_file_accession.values())


async def load_governance_records_using_dao(
    *, records: list[FileGovernanceRecord], dao: FileGovernanceDao
) -> None:
    """Store the given governance records as the full state: delete the records of
    files that are no longer loaded and upsert the new or changed ones.
    """
    existing_records = {
        record.file_accession: record async for record in dao.find_all(filter_={})
    }
    loaded_file_accessions = {record.file_accession for record in records}

    for file_accession in existing_records.keys() - loaded_file_accessions:
        await dao.delete(file_accession)

    for record in records:
        if existing_records.get(record.file_accession) != record:
            await dao.upsert(record)
