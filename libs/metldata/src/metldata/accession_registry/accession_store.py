# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Storing and exploring existing accessions."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class AccessionStoreConfig(BaseSettings):
    """Config parameters and their defaults."""

    accession_store_path: Path = Field(
        ..., description="A file for storing the already registered accessions."
    )


class AccessionStore:
    """A class for storing and querying existing accessions."""

    class AccessionAlreadyExistsError(RuntimeError):
        """Raised when an accession already exists."""

        def __init__(self, *, accession: str):
            message = f"The following accession already exists: {accession}"
            super().__init__(message)

    def __init__(self, *, config: AccessionStoreConfig):
        """Initialize with config parameters."""
        self._config = config

    def exists(self, *, accession: str) -> bool:
        """Checks whether the given accession is already in use."""
        with open(self._config.accession_store_path, encoding="utf-8") as store:
            for existing_accession in store:
                if accession == existing_accession.strip():
                    return True

        return False

    def save(self, *, accession: str) -> None:
        """Save a new accession.

        Raises:
            AccessionAlreadyExistsError: If the given accession already exists.
        """
        if self.exists(accession=accession):
            raise self.AccessionAlreadyExistsError(accession=accession)

        with open(self._config.accession_store_path, "a", encoding="utf-8") as store:
            store.write(f"{accession}\n")
