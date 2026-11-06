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

"""Handling of the accession handler."""

from pydantic import Field
from pydantic_settings import BaseSettings

from ghga_service_commons.utils.accessions import (
    BASE32_ALPHABET,
    DATASET_PID_PREFIX,
    RANDOM_BLOCK_LENGTH,
    STUDY_PID_PREFIX,
)
from ghga_service_commons.utils.utc_dates import now_as_utc
from metldata.accession_registry.accession_registry_utils import (
    find_unused_pid,
    generate_random_block,
)
from metldata.accession_registry.accession_store import AccessionStore

MAX_RANDOM_ATTEMPTS = 100


class AccessionRegistryConfig(BaseSettings):
    """Config parameters and their defaults."""

    study_class_name: str = Field(
        default="Study",
        description=(
            "Name of the metadata model class whose entity takes the bare study PID."
            + " The model does not need to contain it."
        ),
    )

    dataset_class_name: str = Field(
        default="Dataset",
        description=(
            "Name of the metadata model class whose entities are accessioned as"
            + " '{study_pid}.DS.xxx'."
        ),
    )


class AccessionRegistry:
    """Generates the accessions of new resources, registering study PIDs in the
    accession store.
    """

    class AccessionGenerationError(RuntimeError):
        """Raised when a the generation of a new accession failed."""

    def __init__(
        self, *, config: AccessionRegistryConfig, accession_store: AccessionStore
    ):
        """Initialize with config."""
        self._config = config
        self._accession_store = accession_store

    def _compose_study_pid_root(self, *, year: str, random_block: str) -> str:
        """Compose the study PID root 'PREFIX.YY.XXX'."""
        return f"{STUDY_PID_PREFIX}.{year}.{random_block}"

    def _compose_dataset_pid(self, *, study_pid: str, random_block: str) -> str:
        """Compose the dataset PID '{study_pid}.DS.XXX'."""
        return f"{study_pid}.{DATASET_PID_PREFIX}.{random_block}"

    def _choose_unused_study_random_block(self, *, year: str) -> str:
        """Pick a random block of a study PID still unused in the given year.

        Raises:
            AccessionGenerationError: If every study PID root of the year is taken.
        """
        random_block = find_unused_pid(
            alphabet=BASE32_ALPHABET,
            random_block_length=RANDOM_BLOCK_LENGTH,
            compose=lambda random_block: random_block,
            used_pids=self._accession_store.get_random_blocks(year=year),
        )
        if random_block is None:
            raise self.AccessionGenerationError(
                f"All study PIDs of the year '{year}' are in use."
            )

        return random_block

    def generate_study_accession(self) -> str:
        """Generate and register the PID 'PREFIX.YY.XXX.1' of a new study lineage.

        The random block 'XXX' is what gets registered under its year, since it must be
        unique within its year across all versions.

        Raises:
            AccessionGenerationError: If every study PID root of the year is taken.
        """
        # fixed once, so a call crossing midnight on New Year's Eve stays in one year
        year = now_as_utc().strftime("%y")

        for _ in range(MAX_RANDOM_ATTEMPTS):
            random_block = generate_random_block(BASE32_ALPHABET, RANDOM_BLOCK_LENGTH)
            try:
                self._accession_store.save(year=year, random_block=random_block)
            except AccessionStore.AccessionAlreadyExistsError:
                continue

            root = self._compose_study_pid_root(year=year, random_block=random_block)
            return f"{root}.1"

        random_block = self._choose_unused_study_random_block(year=year)
        self._accession_store.save(year=year, random_block=random_block)
        root = self._compose_study_pid_root(year=year, random_block=random_block)

        return f"{root}.1"

    def _choose_unused_dataset_pid(
        self, *, study_pid: str, used_accessions: set[str]
    ) -> str:
        """Pick a dataset PID still unused in the given study.

        Raises:
            AccessionGenerationError: If every dataset PID of the study is taken.
        """
        dataset_pid = find_unused_pid(
            alphabet=BASE32_ALPHABET,
            random_block_length=RANDOM_BLOCK_LENGTH,
            compose=lambda random_block: self._compose_dataset_pid(
                study_pid=study_pid, random_block=random_block
            ),
            used_pids=used_accessions,
        )
        if dataset_pid is None:
            raise self.AccessionGenerationError(
                f"All dataset PIDs of the study '{study_pid}' are in use."
            )

        return dataset_pid

    def generate_dataset_accession(
        self, *, study_pid: str, used_accessions: set[str]
    ) -> str:
        """Generate the PID '{study_pid}.DS.XXX' of a new dataset.

        The random block must be unique among the datasets of the study, so the
        caller passes the accessions the submission holds.

        Raises:
            AccessionGenerationError: If every dataset PID of the study is taken.
        """
        # TODO: across revisions of a study, the epic wants (1) a dataset whose file
        # set is unchanged from the predecessor revision to keep its random block, and
        # (2) a new or changed dataset to get a random block not used anywhere in the
        # lineage. Neither is done yet: every revision draws fresh random blocks,
        # checked only against the datasets of the same revision.
        # For (2), the store will have to keep every dataset block of the lineage.
        for _ in range(MAX_RANDOM_ATTEMPTS):
            random_block = generate_random_block(BASE32_ALPHABET, RANDOM_BLOCK_LENGTH)
            dataset_pid = self._compose_dataset_pid(
                study_pid=study_pid, random_block=random_block
            )
            if dataset_pid not in used_accessions:
                return dataset_pid

        return self._choose_unused_dataset_pid(
            study_pid=study_pid, used_accessions=used_accessions
        )

    def is_study_class(self, class_name: str) -> bool:
        """Tell whether the given class is the one whose entity takes the study PID."""
        return class_name == self._config.study_class_name

    def is_dataset_class(self, class_name: str) -> bool:
        """Tell whether the given class is the one whose entities take dataset PIDs."""
        return class_name == self._config.dataset_class_name

    def generate_accession(
        self, *, class_name: str, alias: str, study_pid: str, used_accessions: set[str]
    ) -> str:
        """Get the accession of a resource of the given class within a study.

        The study entity takes the study PID, and datasets get a PID unique among
        `used_accessions`. Every other resource is accessioned from the study PID and
        its alias by the `add_accessions` transformation, so it gets none here.

        Raises:
            AccessionGenerationError: If the class is neither the study nor the
                dataset class, or every dataset PID of the study is taken.
        """
        if self.is_study_class(class_name):
            return study_pid

        if self.is_dataset_class(class_name):
            return self.generate_dataset_accession(
                study_pid=study_pid, used_accessions=used_accessions
            )

        raise self.AccessionGenerationError(
            f"The class '{class_name}' is neither the study nor the dataset class, so"
            + f" its resource '{alias}' gets no accession from the registry."
        )
