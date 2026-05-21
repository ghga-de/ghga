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
"""DAO translators for accessing the database."""

from hexkit.protocols.dao import DaoFactoryProtocol
from hexkit.providers.mongodb import MongoDbIndex

from fis.core.models import FileUnderInterrogation, InterrogationReport
from fis.ports.outbound.dao import FileDao, InterrogationReportDao


async def get_file_dao(*, dao_factory: DaoFactoryProtocol) -> FileDao:
    """Setup the DAOs using the specified provider of the DaoFactoryProtocol."""
    return await dao_factory.get_dao(
        name="files",
        dto_model=FileUnderInterrogation,
        id_field="id",
        indexes=[MongoDbIndex(fields="object_id")],
    )


async def get_interrogation_report_dao(
    *, dao_factory: DaoFactoryProtocol
) -> InterrogationReportDao:
    """Setup the DAOs using the specified provider of the DaoFactoryProtocol."""
    return await dao_factory.get_dao(
        name="reports",
        dto_model=InterrogationReport,
        id_field="file_id",
    )
