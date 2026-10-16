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

"""Storing and exploring the random blocks of study PIDs already minted."""

import shutil
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings


class AccessionStoreConfig(BaseSettings):
    """Config parameters and their defaults."""

    accession_store_path: Path = Field(
        ...,
        description=(
            "A JSON file holding the random blocks of the study PIDs minted so far, by"
            + " year, so that none is minted twice, and the accessions minted before"
            + " study PIDs."
        ),
    )


class AccessionStoreContent(BaseModel):
    """The content of the accession store file."""

    legacy: list[str] = Field(
        default_factory=list,
        description="Accessions minted under the flat scheme that predates study PIDs.",
    )
    years: dict[str, list[str]] = Field(
        default_factory=dict,
        description="The random blocks of study PIDs minted per two-digit year.",
    )


class AccessionStore:
    """Keeps track of the random blocks of study PIDs per year, so that none is
    minted twice.

    It is an index, not the source of truth: the submission store holds the
    accessions and the metadata they belong to.
    """

    class AccessionAlreadyExistsError(RuntimeError):
        """Raised when a random block already exists in its year."""

        def __init__(self, *, year: str, random_block: str):
            message = (
                f"The random block '{random_block}' already exists in year '{year}'."
            )
            super().__init__(message)

    class InvalidStoreError(RuntimeError):
        """Raised when the store file is not a valid accession store."""

        def __init__(self, *, path: Path):
            message = f"'{path}' is not a valid accession store."
            super().__init__(message)

    class NotALegacyStoreError(RuntimeError):
        """Raised when migrating a store file that is empty or in the JSON format."""

        def __init__(self, *, path: Path):
            message = (
                f"The accession store '{path}' is empty or in the JSON format already,"
                + " so there is nothing to migrate."
            )
            super().__init__(message)

    def __init__(self, *, config: AccessionStoreConfig):
        """Initialize with config parameters."""
        self._config = config

    def _load(self) -> AccessionStoreContent:
        """Load the store content, treating a missing or empty file as empty.

        Raises:
            InvalidStoreError: If the file is not a valid accession store, such as a
                flat list of accessions from before study PIDs.
        """
        path = self._config.accession_store_path
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        if not text.strip():
            return AccessionStoreContent()

        try:
            return AccessionStoreContent.model_validate_json(text)
        except ValidationError as error:
            raise self.InvalidStoreError(path=path) from error

    def _dump(self, content: AccessionStoreContent) -> None:
        """Write the store content to the file."""
        self._config.accession_store_path.write_text(
            content.model_dump_json(indent=2), encoding="utf-8"
        )

    def get_random_blocks(self, *, year: str) -> set[str]:
        """Return the random blocks minted so far in the given year."""
        return set(self._load().years.get(year, []))

    def exists(self, *, year: str, random_block: str) -> bool:
        """Check whether the given random block is already in use in its year."""
        return random_block in self.get_random_blocks(year=year)

    def save(self, *, year: str, random_block: str) -> None:
        """Save a new random block under its year.

        Raises:
            AccessionAlreadyExistsError: If the random block already exists in its year.
        """
        content = self._load()
        random_blocks = content.years.setdefault(year, [])
        if random_block in random_blocks:
            raise self.AccessionAlreadyExistsError(year=year, random_block=random_block)

        random_blocks.append(random_block)
        self._dump(content)

    def migrate_legacy_store(self) -> None:
        """Convert a store file that is a flat list of accessions into the JSON
        format, keeping the accessions under `legacy`.

        Runs once per store, in production only, and is removed from a later release
        once that store is converted. The original file is kept with the suffix '.bak'.

        Raises:
            NotALegacyStoreError: If the file is empty or in the JSON format already.
        """
        path = self._config.accession_store_path
        text = path.read_text(encoding="utf-8")
        # a flat list starts with an accession, never with '{', so a JSON file is
        # refused whether it is valid or not, and never overwrites the backup
        if not text.strip() or text.lstrip().startswith("{"):
            raise self.NotALegacyStoreError(path=path)

        shutil.copy2(path, path.with_name(f"{path.name}.bak"))

        legacy = [line.strip() for line in text.splitlines() if line.strip()]
        self._dump(AccessionStoreContent(legacy=legacy))
