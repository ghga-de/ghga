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

"""Mint accessions in the flat scheme 'prefix + digits' that predates study PIDs, for
amending a submission accessioned under it.

Amendment is the only user, so this module goes with it: metldata keeps the flat
accessions in the store's `legacy` list but no longer mints them.
"""

from collections import Counter
from string import digits

from ghga_datasteward_kit.exceptions import LegacyPrefixMissingError
from metldata.accession_registry.accession_registry import (
    MAX_RANDOM_ATTEMPTS,
    AccessionRegistry,
    AccessionRegistryConfig,
)
from metldata.accession_registry.accession_registry_utils import generate_random_block
from metldata.accession_registry.accession_store import AccessionStore
from metldata.custom_types import Json
from metldata.metadata_utils import lookup_self_id
from metldata.model_utils.anchors import AnchorPoint
from metldata.model_utils.metadata_validator import raise_on_errors

# the prefix per class and the suffix length the flat scheme minted with
LEGACY_PREFIXES = {
    "Study": "GHGAS",
    "ExperimentMethod": "GHGAQ",
    "Experiment": "GHGAX",
    "ResearchDataFile": "GHGAF",
    "ProcessDataFile": "GHGAF",
    "ExperimentMethodSupportingFile": "GHGAF",
    "AnalysisMethodSupportingFile": "GHGAF",
    "IndividualSupportingFile": "GHGAF",
    "DataAccessPolicy": "GHGAP",
    "DataAccessCommittee": "GHGAC",
    "AnalysisMethod": "GHGAZ",
    "Publication": "GHGAU",
    "Analysis": "GHGAR",
    "Individual": "GHGAI",
    "Sample": "GHGAN",
    "Dataset": "GHGAD",
}
LEGACY_SUFFIX_LENGTH = 14


def check_legacy_prefixes(*, anchor_points_by_target: dict[str, AnchorPoint]) -> None:
    """Check that every class of the model has a prefix, so that no accession is
    minted before a class without one stops the amendment.

    Raises:
        LegacyPrefixMissingError: naming each class without a prefix.
    """
    missing = anchor_points_by_target.keys() - LEGACY_PREFIXES.keys()
    if missing:
        raise LegacyPrefixMissingError(class_names=missing)


def check_alias_uniqueness_per_class(
    *, content: Json, anchor_points_by_target: dict[str, AnchorPoint]
) -> None:
    """Check that no two entities of one class share an alias, since they would
    share one accession.

    Raises:
        MetadataValidationError: naming each alias repeated within its class.
    """
    raise_on_errors(
        (
            f"the alias is used by {count} entities of the class"
            + f" '{anchor_point.target_class}', but must be unique within its class",
            "alias",
            alias,
        )
        for anchor_point in anchor_points_by_target.values()
        for alias, count in Counter(
            lookup_self_id(
                resource=resource, identifier_slot=anchor_point.identifier_slot
            )
            for resource in content.get(anchor_point.root_slot, [])
        ).items()
        if count > 1
    )


class LegacyAccessionStore(AccessionStore):
    """Accession store that also registers flat accessions."""

    class LegacyAccessionAlreadyExistsError(RuntimeError):
        """Raised when a flat accession already exists."""

        def __init__(self, *, accession: str):
            super().__init__(f"The accession '{accession}' already exists.")

    def save_legacy(self, *, accession: str) -> None:
        """Save a new flat accession.

        Raises:
            LegacyAccessionAlreadyExistsError: If the accession already exists.
        """
        content = self._load()
        if accession in content.legacy:
            raise self.LegacyAccessionAlreadyExistsError(accession=accession)

        content.legacy.append(accession)
        self._dump(content)


class LegacyAccessionRegistry(AccessionRegistry):
    """Accession registry minting flat accessions instead of study-PID ones."""

    def __init__(
        self, *, config: AccessionRegistryConfig, accession_store: LegacyAccessionStore
    ):
        """Initialize with config."""
        super().__init__(config=config, accession_store=accession_store)
        self._legacy_store = accession_store

    def get_accession(
        self, *, class_name: str, alias: str, study_pid: str, used_accessions: set[str]
    ) -> str:
        """Get the flat accession of a resource of the given class.

        The study keeps its accession, which `generate_accession_map` passes as
        `study_pid`. Every other resource gets a new one, registered in the store.

        Raises:
            AccessionGenerationError: If no unused accession was drawn.
        """
        if self.is_study_class(class_name):
            return study_pid

        prefix = LEGACY_PREFIXES[class_name]
        for _ in range(MAX_RANDOM_ATTEMPTS):
            accession = prefix + generate_random_block(digits, LEGACY_SUFFIX_LENGTH)
            try:
                self._legacy_store.save_legacy(accession=accession)
            except LegacyAccessionStore.LegacyAccessionAlreadyExistsError:
                continue

            return accession

        raise self.AccessionGenerationError(
            f"No unused accession with the prefix '{prefix}' was drawn in"
            + f" {MAX_RANDOM_ATTEMPTS} attempts."
        )
