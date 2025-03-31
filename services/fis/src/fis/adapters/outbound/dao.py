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

from hexkit.protocols.dao import DaoFactoryProtocol

from fis.core.models import FileIdModel
from fis.ports.outbound.dao import FileDao


async def get_file_dao(*, dao_factory: DaoFactoryProtocol) -> FileDao:
    """Setup the DAOs using the specified provider of the DaoFactoryProtocol."""
    return await dao_factory.get_dao(
        name="ingestedFiles",
        dto_model=FileIdModel,
        id_field="file_id",
    )
