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

from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class AccessionStoreConfig(BaseSettings):
    """Config parameters and their defaults."""

    accession_store_path: Path = Field(
        ...,
        description=(
            "A JSON file holding the random blocks of the study PIDs minted so far, by"
            + " year, so that none is minted twice."
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

    def __init__(self, *, config: AccessionStoreConfig):
        """Initialize with config parameters."""
        self._config = config

    def _load(self) -> AccessionStoreContent:
        """Load the store content, treating a missing or empty file as empty."""
        path = self._config.accession_store_path
        if not path.exists() or not path.read_text(encoding="utf-8").strip():
            return AccessionStoreContent()

        return AccessionStoreContent.model_validate_json(
            path.read_text(encoding="utf-8")
        )

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
