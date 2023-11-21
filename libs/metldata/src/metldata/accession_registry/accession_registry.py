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

"""Handling of the accession handler."""

import secrets
from collections.abc import Iterable

from pydantic import Field
from pydantic_settings import BaseSettings

from metldata.accession_registry.accession_store import AccessionStore


class AccessionRegistryConfig(BaseSettings):
    """Config parameters and their defaults."""

    prefix_mapping: dict[str, str] = Field(
        ...,
        description="Specifies the ID prefix (values) per resource type (keys).",
        examples=[
            {
                "file": "GHGAF",
                "experiment": "GHGAE",
                "sample": "GHGAS",
                "dataset": "GHGAD",
            }
        ],
    )

    suffix_length: int = Field(8, description="Length of the numeric ID suffix.")


class AccessionRegistry:
    """Main class handling the accession registry."""

    class UnkownResourceTypeError(RuntimeError):
        """Raised when a resource type is specified that is unkown."""

        def __init__(self, *, specified_type: str, expected_types: Iterable[str]):
            """Specify the given as well as the expected resource types."""
            message = (
                f"The specified resource type '{specified_type} is unkown'."
                + " Expected one of: "
                + ", ".join(expected_types)
            )
            super().__init__(message)

    class AccessionGenerationError(RuntimeError):
        """Raised when a the generation of a new accession failed."""

    def __init__(
        self, *, config: AccessionRegistryConfig, accession_store: AccessionStore
    ):
        """Initialize with config."""
        self._config = config
        self._accession_store = accession_store

    def _assert_resource_type_exists(self, *, resource_type: str) -> None:
        """Checks whether the specified resource type is in the prefix mapping, raises
        and UnkownResourceTypeError otherwise.
        """
        if resource_type not in self._config.prefix_mapping:
            raise self.UnkownResourceTypeError(
                specified_type=resource_type,
                expected_types=self._config.prefix_mapping.keys(),
            )

    def _generate_accession(self, *, resource_type: str) -> str:
        """Generate a new accession."""
        self._assert_resource_type_exists(resource_type=resource_type)

        prefix = self._config.prefix_mapping[resource_type]
        suffix = "".join(
            str(secrets.randbelow(10)) for _ in range(self._config.suffix_length)
        )

        return prefix + suffix

    def get_accession(self, *, resource_type: str) -> str:
        """Generates and registers a new accession for a resource of the specified type."""
        for _ in range(10):
            # try 10 times to generate a new accession:
            accession = self._generate_accession(resource_type=resource_type)

            try:
                self._accession_store.save(accession=accession)
            except AccessionStore.AccessionAlreadyExistsError:
                continue

            return accession

        raise self.AccessionGenerationError(
            "Tried and failed 10 times to generate a new accession that is not used"
            + " already. The accession space might be exhausted."
        )
