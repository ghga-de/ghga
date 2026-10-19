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

"""Resolve the data access policy and committee that govern a file.

The traversal goes file -> dataset -> data_access_policy -> data_access_committee.
It works on submissions from the submission store and on artifact contents.
"""

from collections import defaultdict
from collections.abc import Iterable, Sequence

from pydantic import BaseModel, Field

from metldata.custom_types import Json
from metldata.submission_registry.models import Submission

FILE_CLASS_SLOT_SUFFIX = "_files"
DATASET_CLASS_SLOT = "datasets"
DATA_ACCESS_POLICY_CLASS_SLOT = "data_access_policies"
DATA_ACCESS_COMMITTEE_CLASS_SLOT = "data_access_committees"
REUSED_ACCESSION_SLOT = "reused_accession"

# Governance is compared by content only, so these slots are left out of it.
IDENTITY_SLOTS = frozenset({"accession", "alias", "ega_accession"})


class GovernanceResolutionError(RuntimeError):
    """Raised when a reference on the governance chain cannot be resolved."""

    def __init__(self, *, class_slot: str, reference: str):
        super().__init__(
            f"Could not resolve reference '{reference}' in class slot '{class_slot}'."
        )


class FileGovernance(BaseModel):
    """The governance of a file through one of its datasets.

    Accessions are None for resources that have no accession yet.
    """

    dataset_accession: str | None = Field(
        ..., description="Accession of the dataset the file belongs to."
    )
    data_access_policy_accession: str | None = Field(
        ..., description="Accession of the dataset's data access policy."
    )
    data_access_policy: Json = Field(
        ...,
        description=(
            "Content of the data access policy, without identity slots and without"
            + " the reference to its data access committee."
        ),
    )
    data_access_committee_accession: str | None = Field(
        ..., description="Accession of the policy's data access committee."
    )
    data_access_committee_alias: str = Field(
        ..., description="Alias of the data access committee."
    )
    data_access_committee: Json = Field(
        ..., description="Content of the data access committee, without identity slots."
    )


class GovernanceMetadata:
    """Metadata documents indexed for the governance traversal.

    Each document maps class slots to lists of resources. Resources carry an
    `accession` if one was minted. References hold the value of `reference_slot`
    and resolve within their own document. Use `from_submissions` or
    `from_artifacts` to create an instance.
    """

    def __init__(self, *, documents: Sequence[Json], reference_slot: str):
        self._reference_slot = reference_slot
        self._resources_by_reference: list[dict[str, dict[str, Json]]] = [
            {
                class_slot: {
                    resource[reference_slot]: resource
                    for resource in document.get(class_slot, [])
                    if reference_slot in resource
                }
                for class_slot in (
                    DATASET_CLASS_SLOT,
                    DATA_ACCESS_POLICY_CLASS_SLOT,
                    DATA_ACCESS_COMMITTEE_CLASS_SLOT,
                )
            }
            for document in documents
        ]
        self._index_files(documents=documents)

    @classmethod
    def from_submissions(cls, *, submissions: Sequence[Submission]):
        """Index submissions. References are aliases, and accessions come from the
        accession map.
        """
        documents = [
            {
                class_slot: [
                    _with_accession(
                        resource=resource,
                        accession=submission.accession_map.get(class_slot, {}).get(
                            resource.get("alias", "")
                        ),
                    )
                    for resource in resources
                ]
                for class_slot, resources in (submission.content or {}).items()
            }
            for submission in submissions
        ]
        return cls(documents=documents, reference_slot="alias")

    @classmethod
    def from_artifacts(cls, *, contents: Sequence[Json]):
        """Index artifact contents in which references are accessions, such as
        `added_accessions`.
        """
        return cls(documents=contents, reference_slot="accession")

    def _index_files(self, *, documents: Sequence[Json]) -> None:
        """Group file resources by physical file.

        A file resource is grouped with the file it reuses. If B reuses A's file
        and C reuses B's, all three resources are in one group.
        """
        parent: dict[str, str] = {}

        def find(accession: str) -> str:
            parent.setdefault(accession, accession)
            while parent[accession] != accession:
                parent[accession] = parent[parent[accession]]
                accession = parent[accession]
            return accession

        files_with_accessions: list[tuple[int, Json, list[str]]] = []
        for scope, document in enumerate(documents):
            for class_slot, resources in document.items():
                if not class_slot.endswith(FILE_CLASS_SLOT_SUFFIX):
                    continue
                for file in resources:
                    accessions = [
                        accession
                        for accession in (
                            file.get("accession"),
                            file.get(REUSED_ACCESSION_SLOT),
                        )
                        if accession
                    ]
                    for accession in accessions[1:]:
                        parent[find(accession)] = find(accessions[0])
                    files_with_accessions.append((scope, file, accessions))

        self._find_physical_file = find
        self._files_by_physical_file: dict[str, list[tuple[int, Json]]] = defaultdict(
            list
        )
        for scope, file, accessions in files_with_accessions:
            if accessions:
                self._files_by_physical_file[find(accessions[0])].append((scope, file))

    def find_files(self, *, file_accession: str) -> list[tuple[int, Json]]:
        """Return the resources of the physical file with the given accession, each
        with the index of its document.
        """
        return list(
            self._files_by_physical_file.get(
                self._find_physical_file(file_accession), []
            )
        )

    def resolve(
        self, *, scope: int, resource: Json, slot_name: str, class_slot: str
    ) -> Json:
        """Follow the reference in a resource's slot to the referenced resource."""
        reference = resource.get(slot_name)
        if not isinstance(reference, str):
            raise GovernanceResolutionError(
                class_slot=class_slot,
                reference=f"<slot '{slot_name}' of resource"
                + f" '{resource.get(self._reference_slot)}'>",
            )
        try:
            return self._resources_by_reference[scope][class_slot][reference]
        except KeyError as error:
            raise GovernanceResolutionError(
                class_slot=class_slot, reference=reference
            ) from error


def _with_accession(*, resource: Json, accession: str | None) -> Json:
    return {**resource, "accession": accession} if accession else resource


def _strip_slots(*, resource: Json, slot_names: Iterable[str]) -> Json:
    excluded_slots = set(slot_names)
    return {key: value for key, value in resource.items() if key not in excluded_slots}


def resolve_file_governance(
    *, file_accession: str, metadata: GovernanceMetadata
) -> list[FileGovernance]:
    """Resolve the governance of a physical file, one entry per dataset.

    Files match by their own accession and by their reused accession. The result
    includes every study in `metadata` that uses the file, so callers choose which
    documents to pass. Returns an empty list if no file matches. Raises a
    GovernanceResolutionError if a reference is dangling.
    """
    governance_by_dataset: dict[str | tuple[int, str], FileGovernance] = {}

    for scope, file in metadata.find_files(file_accession=file_accession):
        dataset = metadata.resolve(
            scope=scope,
            resource=file,
            slot_name="dataset",
            class_slot=DATASET_CLASS_SLOT,
        )
        # Two artifact types of one study hold the same dataset. Datasets without
        # an accession are distinct per document.
        dataset_key = dataset.get("accession") or (scope, file["dataset"])
        if dataset_key in governance_by_dataset:
            continue

        data_access_policy = metadata.resolve(
            scope=scope,
            resource=dataset,
            slot_name="data_access_policy",
            class_slot=DATA_ACCESS_POLICY_CLASS_SLOT,
        )
        data_access_committee = metadata.resolve(
            scope=scope,
            resource=data_access_policy,
            slot_name="data_access_committee",
            class_slot=DATA_ACCESS_COMMITTEE_CLASS_SLOT,
        )

        governance_by_dataset[dataset_key] = FileGovernance(
            dataset_accession=dataset.get("accession"),
            data_access_policy_accession=data_access_policy.get("accession"),
            data_access_policy=_strip_slots(
                resource=data_access_policy,
                slot_names=IDENTITY_SLOTS | {"data_access_committee"},
            ),
            data_access_committee_accession=data_access_committee.get("accession"),
            data_access_committee_alias=data_access_committee.get("alias", ""),
            data_access_committee=_strip_slots(
                resource=data_access_committee, slot_names=IDENTITY_SLOTS
            ),
        )

    return list(governance_by_dataset.values())


def resolve_files_governance(
    *, file_accessions: Iterable[str], metadata: GovernanceMetadata
) -> dict[str, list[FileGovernance]]:
    """Resolve the governance of several files, keyed by file accession."""
    return {
        file_accession: resolve_file_governance(
            file_accession=file_accession, metadata=metadata
        )
        for file_accession in file_accessions
    }
