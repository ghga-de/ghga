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

from ghga_service_commons.utils.utc_dates import now_as_utc
from metldata.accession_registry.accession_registry_utils import (
    LEGACY_STUDY_ACCESSION_PATTERN,
    find_unused_pid,
    generate_random_block,
    study_pid_pattern,
)
from metldata.accession_registry.accession_store import AccessionStore

# RFC 4648 base32. Not configurable: removing or reassigning a character could
# invalidate PIDs already minted.
BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"

MAX_RANDOM_ATTEMPTS = 100


class AccessionRegistryConfig(BaseSettings):
    """Config parameters and their defaults."""

    study_pid_prefix: str = Field(
        default="GHGA",
        pattern=r"^[^.]+$",
        description=(
            "The leading block of the study PID 'PREFIX.YY.XXX.V'. Must not contain"
            + " dots, as they separate the blocks of the PID."
        ),
    )

    dataset_pid_prefix: str = Field(
        default="DS",
        pattern=r"^[^.]+$",
        description=(
            "The part of a dataset PID '{study_pid}.DS.XXX' that marks it as a"
            + " dataset. Must not contain dots, as they separate the blocks of the PID."
        ),
    )

    random_block_length: int = Field(
        default=3,
        ge=1,
        description=(
            "Number of base32 characters (RFC 4648) in the random block of a study PID"
            + " ('XXX') and of a dataset accession ('DS.xxx')."
        ),
    )

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
    """Main class handling the accession registry."""

    class AccessionGenerationError(RuntimeError):
        """Raised when a the generation of a new accession failed."""

    class InvalidPredecessorError(ValueError):
        """Raised when a predecessor PID is neither a legacy study accession nor a
        study PID minted by this registry.
        """

    def __init__(
        self, *, config: AccessionRegistryConfig, accession_store: AccessionStore
    ):
        """Initialize with config."""
        self._config = config
        self._accession_store = accession_store

    def _compose_study_pid_root(self, *, year: str, random_block: str) -> str:
        """Compose the study PID root 'PREFIX.YY.XXX'."""
        return f"{self._config.study_pid_prefix}.{year}.{random_block}"

    def _compose_dataset_pid(self, *, study_pid: str, random_block: str) -> str:
        """Compose the dataset PID '{study_pid}.DS.XXX'."""
        return f"{study_pid}.{self._config.dataset_pid_prefix}.{random_block}"

    def _choose_unused_study_random_block(self, *, year: str) -> str:
        """Pick a random block of a study PID still unused in the given year.

        Raises:
            AccessionGenerationError: If every study PID root of the year is taken.
        """
        random_block = find_unused_pid(
            alphabet=BASE32_ALPHABET,
            random_block_length=self._config.random_block_length,
            compose=lambda random_block: random_block,
            used_pids=self._accession_store.get_random_blocks(year=year),
        )
        if random_block is None:
            raise self.AccessionGenerationError(
                f"All study PIDs of the year '{year}' are in use."
            )

        return random_block

    def _mint_fresh_study_pid(self) -> str:
        """Generate and register the PID 'PREFIX.YY.XXX.1' of a new study lineage.

        The random block 'XXX' is what gets registered under its year, since it must be
        unique within its year across all versions.

        Raises:
            AccessionGenerationError: If every study PID root of the year is taken.
        """
        # fixed once, so a call crossing midnight on New Year's Eve stays in one year
        year = now_as_utc().strftime("%y")

        for _ in range(MAX_RANDOM_ATTEMPTS):
            random_block = generate_random_block(
                BASE32_ALPHABET, self._config.random_block_length
            )
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

    def _continue_study_pid(self, *, predecessor_pid: str) -> str:
        """Continue the lineage of a study PID: same root, version + 1.

        Nothing is registered, since the root was registered when its lineage started.

        Raises:
            InvalidPredecessorError: If the predecessor is not a well-formed study PID
                or its root was never registered.
        """
        match = study_pid_pattern(
            self._config.study_pid_prefix,
            BASE32_ALPHABET,
            self._config.random_block_length,
        ).match(predecessor_pid)
        if match is None:
            raise self.InvalidPredecessorError(
                f"'{predecessor_pid}' is neither a legacy study accession nor a study"
                + " PID."
            )

        root, version = match.group(1), int(match.group(2))
        # the prefix holds no dots, so the root splits into exactly its three parts
        _, year, random_block = root.split(".")
        if not self._accession_store.exists(year=year, random_block=random_block):
            raise self.InvalidPredecessorError(
                f"The study PID '{predecessor_pid}' was never minted."
            )

        return f"{root}.{version + 1}"

    def get_study_accession(self, *, predecessor_pid: str | None = None) -> str:
        """Get the PID of a study, given the PID of the study it replaces, if any.

        A new study, or one replacing a legacy study accession, starts a fresh lineage
        'PREFIX.YY.XXX.1'. One replacing a study PID continues that lineage with the
        version increased by one.

        Raises:
            AccessionGenerationError: If every study PID root of the year is taken.
            InvalidPredecessorError: If the predecessor is not a valid study PID.
        """
        if predecessor_pid is None or LEGACY_STUDY_ACCESSION_PATTERN.match(
            predecessor_pid
        ):
            return self._mint_fresh_study_pid()

        return self._continue_study_pid(predecessor_pid=predecessor_pid)

    def _choose_unused_dataset_pid(
        self, *, study_pid: str, used_dataset_pids: set[str]
    ) -> str:
        """Pick a dataset PID still unused in the given study.

        Raises:
            AccessionGenerationError: If every dataset PID of the study is taken.
        """
        dataset_pid = find_unused_pid(
            alphabet=BASE32_ALPHABET,
            random_block_length=self._config.random_block_length,
            compose=lambda random_block: self._compose_dataset_pid(
                study_pid=study_pid, random_block=random_block
            ),
            used_pids=used_dataset_pids,
        )
        if dataset_pid is None:
            raise self.AccessionGenerationError(
                f"All dataset PIDs of the study '{study_pid}' are in use."
            )

        return dataset_pid

    def get_dataset_accession(
        self, *, study_pid: str, used_dataset_pids: set[str]
    ) -> str:
        """Generate the PID '{study_pid}.DS.XXX' of a new dataset.

        The random block must be unique among the datasets of the study, so the caller
        passes the dataset PIDs already given out in it. Nothing is registered in the
        store, since the dataset PID is unique by construction once the study PID is.

        Raises:
            AccessionGenerationError: If every dataset PID of the study is taken.
        """
        # TODO: across revisions of a study, the epic wants (1) a dataset whose file
        # set is unchanged from the predecessor revision to keep its random block, and
        # (2) a new or changed dataset to get a random block not used anywhere in the
        # lineage. Neither is done yet: every revision draws fresh random blocks,
        # checked only against the datasets of the same revision.
        for _ in range(MAX_RANDOM_ATTEMPTS):
            random_block = generate_random_block(
                BASE32_ALPHABET, self._config.random_block_length
            )
            dataset_pid = self._compose_dataset_pid(
                study_pid=study_pid, random_block=random_block
            )
            if dataset_pid not in used_dataset_pids:
                return dataset_pid

        return self._choose_unused_dataset_pid(
            study_pid=study_pid, used_dataset_pids=used_dataset_pids
        )

    def get_alias_accession(self, *, study_pid: str, alias: str) -> str:
        """Compose the accession '{study_pid}.{alias}' of an entity that is neither
        the study nor a dataset.

        Nothing is drawn or registered: the accession is unique by construction, since
        the study PID is unique and aliases are unique within the study.
        """
        return f"{study_pid}.{alias}"

    def is_study_class(self, class_name: str) -> bool:
        """Tell whether the given class is the one whose entity takes the study PID."""
        return class_name == self._config.study_class_name

    def get_accession(
        self, *, class_name: str, alias: str, study_pid: str, used_accessions: set[str]
    ) -> str:
        """Get the accession of a resource of the given class within a study.

        The study entity takes the study PID, datasets get a PID unique among
        `used_accessions`, and every other resource is accessioned by its alias.

        Raises:
            AccessionGenerationError: If every dataset PID of the study is taken.
        """
        if self.is_study_class(class_name):
            return study_pid

        if class_name == self._config.dataset_class_name:
            return self.get_dataset_accession(
                study_pid=study_pid, used_dataset_pids=used_accessions
            )

        return self.get_alias_accession(study_pid=study_pid, alias=alias)
