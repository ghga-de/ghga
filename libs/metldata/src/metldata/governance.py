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
    data_access_committee_alias: str | None = Field(
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
        `resolved_restricted`. Embedded artifacts are not supported, because they
        nest the policy in the dataset instead of referencing it.
        """
        return cls(documents=contents, reference_slot="accession")

    def _index_files(self, *, documents: Sequence[Json]) -> None:
        """Index file resources by their own accession and by their reused
        accession, and group accessions linked by reuse into chains.
        """
        self._files_by_accession: dict[str, list[tuple[int, int, Json]]] = defaultdict(
            list
        )
        linked_accessions: dict[str, set[str]] = defaultdict(set)
        position = 0
        for document_index, document in enumerate(documents):
            for class_slot, resources in document.items():
                if not class_slot.endswith(FILE_CLASS_SLOT_SUFFIX):
                    continue
                for file in resources:
                    own_and_reused_accessions = {
                        file.get("accession"),
                        file.get(REUSED_ACCESSION_SLOT),
                    } - {None, ""}
                    for accession in own_and_reused_accessions:
                        self._files_by_accession[accession].append(
                            (position, document_index, file)
                        )
                        linked_accessions[accession] |= own_and_reused_accessions
                    position += 1

        self._reuse_chain_by_accession = _group_reuse_chains(
            linked_accessions=linked_accessions
        )

    def find_files(
        self, *, file_accession: str, follow_reuse_chain: bool = False
    ) -> list[tuple[int, Json]]:
        """Return the file resources whose own or reused accession is the given one,
        each with the index of its document, in document order.

        With `follow_reuse_chain`, match every accession in the reuse chain of the
        given one instead.
        """
        accessions = (
            self._reuse_chain_by_accession.get(file_accession, {file_accession})
            if follow_reuse_chain
            else {file_accession}
        )
        files_by_position = {
            position: (document_index, file)
            for accession in accessions
            for position, document_index, file in self._files_by_accession.get(
                accession, []
            )
        }
        return [files_by_position[position] for position in sorted(files_by_position)]

    def resolve(
        self, *, document_index: int, resource: Json, slot_name: str, class_slot: str
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
            return self._resources_by_reference[document_index][class_slot][reference]
        except KeyError as error:
            raise GovernanceResolutionError(
                class_slot=class_slot, reference=reference
            ) from error


def _group_reuse_chains(
    *, linked_accessions: dict[str, set[str]]
) -> dict[str, frozenset[str]]:
    """Map each accession to its reuse chain. Reuse links count in both directions,
    so a chain is a connected component.
    """
    chain_by_accession: dict[str, frozenset[str]] = {}
    for start_accession in linked_accessions:
        if start_accession in chain_by_accession:
            continue
        chain = {start_accession}
        pending = [start_accession]
        while pending:
            for linked_accession in linked_accessions[pending.pop()]:
                if linked_accession not in chain:
                    chain.add(linked_accession)
                    pending.append(linked_accession)
        frozen_chain = frozenset(chain)
        for accession in chain:
            chain_by_accession[accession] = frozen_chain
    return chain_by_accession


def _with_accession(*, resource: Json, accession: str | None) -> Json:
    return {**resource, "accession": accession} if accession else resource


def _strip_slots(*, resource: Json, slot_names: Iterable[str]) -> Json:
    excluded_slots = set(slot_names)
    return {key: value for key, value in resource.items() if key not in excluded_slots}


def resolve_file_governance(
    *,
    file_accession: str,
    metadata: GovernanceMetadata,
    follow_reuse_chain: bool = False,
) -> list[FileGovernance]:
    """Resolve the governance of a file accession, one entry per dataset.

    Files match by their own accession and by their reused accession. With
    `follow_reuse_chain`, every file in the reuse chain of the accession matches.

    The result covers every document in `metadata`, so callers choose the documents:
    - Loader: metadata from the artifact being loaded only, querying its own file
      accessions.
    - Submit-path governance finding: "new" is metadata from the new submission
      only, querying the reused accession. "Before" is metadata from prior
      submissions only, querying the reused accession with
      `follow_reuse_chain=True`.

    Returns an empty list if no file matches. Raises a GovernanceResolutionError if
    a reference is dangling.
    """
    governance_by_dataset: dict[str | tuple[int, str], FileGovernance] = {}

    for document_index, file in metadata.find_files(
        file_accession=file_accession, follow_reuse_chain=follow_reuse_chain
    ):
        dataset = metadata.resolve(
            document_index=document_index,
            resource=file,
            slot_name="dataset",
            class_slot=DATASET_CLASS_SLOT,
        )
        # Two artifact types of one study hold the same dataset. Datasets without
        # an accession are distinct per document.
        dataset_key = dataset.get("accession") or (document_index, file["dataset"])
        if dataset_key in governance_by_dataset:
            continue

        data_access_policy = metadata.resolve(
            document_index=document_index,
            resource=dataset,
            slot_name="data_access_policy",
            class_slot=DATA_ACCESS_POLICY_CLASS_SLOT,
        )
        data_access_committee = metadata.resolve(
            document_index=document_index,
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
            data_access_committee_alias=data_access_committee.get("alias"),
            data_access_committee=_strip_slots(
                resource=data_access_committee, slot_names=IDENTITY_SLOTS
            ),
        )

    return list(governance_by_dataset.values())


def resolve_files_governance(
    *,
    file_accessions: Iterable[str],
    metadata: GovernanceMetadata,
    follow_reuse_chain: bool = False,
) -> dict[str, list[FileGovernance]]:
    """Resolve the governance of several files, keyed by file accession."""
    return {
        file_accession: resolve_file_governance(
            file_accession=file_accession,
            metadata=metadata,
            follow_reuse_chain=follow_reuse_chain,
        )
        for file_accession in file_accessions
    }
