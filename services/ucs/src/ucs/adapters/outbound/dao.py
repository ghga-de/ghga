# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""DAO translators for accessing the database."""

from dataclasses import dataclass

from hexkit.protocols.dao import DaoFactoryProtocol

from ucs.core import models
from ucs.ports.outbound.dao import DaoCollectionPort


@dataclass
class DaoCollectionTranslator:
    """Constructor compatible with the hexkit.inject.AsyncConstructable type. Used to
    construct a collection of DAOs for interacting with the database.
    """

    @staticmethod
    async def construct(*, provider: DaoFactoryProtocol) -> DaoCollectionPort:
        """Setup a collection of DAOs using the specified provider of the
        DaoFactoryProtocol.
        """
        file_metadata = await provider.get_dao(
            name="file_metadata", dto_model=models.FileMetadata, id_field="file_id"
        )
        upload_attempts = await provider.get_dao(
            name="upload_attempts", dto_model=models.UploadAttempt, id_field="upload_id"
        )

        return DaoCollectionPort(
            file_metadata=file_metadata, upload_attempts=upload_attempts
        )
