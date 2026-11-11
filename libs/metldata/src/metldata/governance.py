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

The traversal goes file -> dataset -> data access policy -> data access committee,
along the classes and slots named in `metldata.model_utils.essentials`. It works on
submissions from the submission store and on artifact contents.
"""

from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from functools import partial

from pydantic import BaseModel, Field

from metldata.custom_types import Json
from metldata.metadata_utils import lookup_self_id
from metldata.model_utils.anchors import AnchorPoint, filter_anchor_points
from metldata.model_utils.essentials import (
    ALIAS_SLOT,
    DATA_ACCESS_COMMITTEE_CLASS,
    DATA_ACCESS_POLICY_CLASS,
    DATA_ACCESS_POLICY_DATA_ACCESS_COMMITTEE_SLOT,
    DATASET_CLASS,
    DATASET_DATA_ACCESS_POLICY_SLOT,
    EGA_ACCESSION_SLOT,
    FILE_CLASS_SUFFIX,
    FILE_DATASET_SLOT,
    REUSED_ACCESSION_SLOT,
)
from metldata.submission_registry.identifiers import lookup_accession
from metldata.submission_registry.models import AccessionMap, Submission

GOVERNANCE_CLASSES = (
    DATASET_CLASS,
    DATA_ACCESS_POLICY_CLASS,
    DATA_ACCESS_COMMITTEE_CLASS,
)


class GovernanceResolutionError(RuntimeError):
    """Raised when a reference on the governance chain cannot be resolved."""

    def __init__(self, *, root_slot: str, reference: str):
        super().__init__(
            f"Could not resolve reference '{reference}' in root slot '{root_slot}'."
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


@dataclass(frozen=True)
class GovernanceResource:
    """A resource on the governance chain, with its identity slots split from its
    content.
    """

    identifier: str
    accession: str | None
    alias: str | None
    content: Json


# Looks up the accession of a resource from its anchor point and identifier.
AccessionLookup = Callable[[AnchorPoint, str], str | None]


class GovernanceMetadata:
    """Metadata documents indexed for the governance traversal.

    Each submission or artifact content maps the root slots, such as `datasets`, to
    the resources of that class, and is indexed as one document. A reference holds
    the identifier slot value of the resource it refers to and resolves within its
    own document. Use `from_submissions` or `from_artifacts` to create an instance.
    """

    def __init__(
        self,
        *,
        documents: Sequence[dict[str, list[GovernanceResource]]],
        anchor_points_by_target: dict[str, AnchorPoint],
    ):
        self._anchor_points_by_target = anchor_points_by_target
        self._resources_by_identifier: list[
            dict[str, dict[str, GovernanceResource]]
        ] = [
            {
                class_name: {
                    resource.identifier: resource
                    for resource in document.get(class_name, [])
                }
                for class_name in GOVERNANCE_CLASSES
            }
            for document in documents
        ]
        self._index_files(documents=documents)

    @classmethod
    def from_submissions(
        cls,
        *,
        submissions: Sequence[Submission],
        anchor_points_by_target: dict[str, AnchorPoint],
    ):
        """Index submissions. Identifier slots hold aliases, and accessions come from
        the accession map.

        Raises:
            AnchorPointNotFoundError: if a class on the governance chain is not
                anchored.
        """
        governance_anchor_points = _filter_governance_anchor_points(
            anchor_points_by_target=anchor_points_by_target
        )
        documents = [
            _index_document(
                content=submission.content or {},
                anchor_points_by_target=governance_anchor_points,
                lookup_resource_accession=partial(
                    _lookup_submission_accession,
                    accession_map=submission.accession_map,
                ),
            )
            for submission in submissions
        ]
        return cls(
            documents=documents, anchor_points_by_target=governance_anchor_points
        )

    @classmethod
    def from_artifacts(
        cls,
        *,
        contents: Sequence[Json],
        anchor_points_by_target: dict[str, AnchorPoint],
    ):
        """Index artifact contents in which identifier slots hold accessions, such as
        `resolved_restricted`. Embedded artifacts are not supported, because they
        nest the policy in the dataset instead of referencing it.

        Raises:
            AnchorPointNotFoundError: if a class on the governance chain is not
                anchored.
        """
        governance_anchor_points = _filter_governance_anchor_points(
            anchor_points_by_target=anchor_points_by_target
        )
        documents = [
            _index_document(
                content=content,
                anchor_points_by_target=governance_anchor_points,
                lookup_resource_accession=lambda _anchor_point, accession: accession,
            )
            for content in contents
        ]
        return cls(
            documents=documents, anchor_points_by_target=governance_anchor_points
        )

    def _index_files(
        self, *, documents: Sequence[dict[str, list[GovernanceResource]]]
    ) -> None:
        """Index file resources by their own accession and by their reused
        accession, and group accessions linked by reuse into chains.
        """
        self._files_by_accession: dict[
            str, list[tuple[int, int, GovernanceResource]]
        ] = defaultdict(list)
        linked_accessions: dict[str, set[str]] = defaultdict(set)
        position = 0
        for document_index, document in enumerate(documents):
            for class_name, resources in document.items():
                if not class_name.endswith(FILE_CLASS_SUFFIX):
                    continue
                for file in resources:
                    own_and_reused_accessions: set[str] = {
                        accession
                        for accession in (
                            file.accession,
                            file.content.get(REUSED_ACCESSION_SLOT),
                        )
                        if accession
                    }
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
    ) -> list[tuple[int, GovernanceResource]]:
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
        self,
        *,
        document_index: int,
        resource: GovernanceResource,
        slot_name: str,
        class_name: str,
    ) -> GovernanceResource:
        """Follow the reference in a resource's slot to the referenced resource of
        the given class.
        """
        root_slot = self._anchor_points_by_target[class_name].root_slot
        reference = resource.content.get(slot_name)
        if not isinstance(reference, str):
            raise GovernanceResolutionError(
                root_slot=root_slot,
                reference=f"<slot '{slot_name}' of resource '{resource.identifier}'>",
            )
        try:
            return self._resources_by_identifier[document_index][class_name][reference]
        except KeyError as error:
            raise GovernanceResolutionError(
                root_slot=root_slot, reference=reference
            ) from error


def _filter_governance_anchor_points(
    *, anchor_points_by_target: dict[str, AnchorPoint]
) -> dict[str, AnchorPoint]:
    """Keep the anchor points of the file classes and of the GOVERNANCE_CLASSES.

    Raises:
        AnchorPointNotFoundError: if one of the GOVERNANCE_CLASSES is not anchored.
    """
    file_classes = {
        class_name
        for class_name in anchor_points_by_target
        if class_name.endswith(FILE_CLASS_SUFFIX)
    }
    return filter_anchor_points(
        anchor_points_by_target=anchor_points_by_target,
        classes_of_interest=file_classes | set(GOVERNANCE_CLASSES),
    )


def _index_document(
    *,
    content: Json,
    anchor_points_by_target: dict[str, AnchorPoint],
    lookup_resource_accession: AccessionLookup,
) -> dict[str, list[GovernanceResource]]:
    """Map the class names of the anchor points to the resources of that class in
    the content. Identity slots are split from each resource's content.
    """
    document: dict[str, list[GovernanceResource]] = {}
    for class_name, anchor_point in anchor_points_by_target.items():
        identity_slots = {anchor_point.identifier_slot, ALIAS_SLOT, EGA_ACCESSION_SLOT}
        resources = []
        for resource in content.get(anchor_point.root_slot, []):
            identifier = lookup_self_id(
                resource=resource, identifier_slot=anchor_point.identifier_slot
            )
            resources.append(
                GovernanceResource(
                    identifier=identifier,
                    accession=lookup_resource_accession(anchor_point, identifier),
                    alias=resource.get(ALIAS_SLOT),
                    content=_strip_slots(resource=resource, slot_names=identity_slots),
                )
            )
        document[class_name] = resources
    return document


def _lookup_submission_accession(
    anchor_point: AnchorPoint, alias: str, *, accession_map: AccessionMap
) -> str | None:
    """Look up the accession of a submission's resource in its accession map."""
    return lookup_accession(
        anchor=anchor_point.root_slot, alias=alias, accession_map=accession_map
    )


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
            slot_name=FILE_DATASET_SLOT,
            class_name=DATASET_CLASS,
        )
        # Two artifact types of one study hold the same dataset. Datasets without
        # an accession are distinct per document.
        dataset_key = dataset.accession or (document_index, dataset.identifier)
        if dataset_key in governance_by_dataset:
            continue

        data_access_policy = metadata.resolve(
            document_index=document_index,
            resource=dataset,
            slot_name=DATASET_DATA_ACCESS_POLICY_SLOT,
            class_name=DATA_ACCESS_POLICY_CLASS,
        )
        data_access_committee = metadata.resolve(
            document_index=document_index,
            resource=data_access_policy,
            slot_name=DATA_ACCESS_POLICY_DATA_ACCESS_COMMITTEE_SLOT,
            class_name=DATA_ACCESS_COMMITTEE_CLASS,
        )

        governance_by_dataset[dataset_key] = FileGovernance(
            dataset_accession=dataset.accession,
            data_access_policy_accession=data_access_policy.accession,
            data_access_policy=_strip_slots(
                resource=data_access_policy.content,
                slot_names={DATA_ACCESS_POLICY_DATA_ACCESS_COMMITTEE_SLOT},
            ),
            data_access_committee_accession=data_access_committee.accession,
            data_access_committee_alias=data_access_committee.alias,
            data_access_committee=data_access_committee.content,
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
