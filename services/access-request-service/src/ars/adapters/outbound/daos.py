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
#

"""DAO translators for accessing the database."""

from hexkit.protocols.dao import DaoFactoryProtocol

from ars.core import models
from ars.ports.outbound.daos import AccessRequestDaoPort, DatasetDaoPort

__all__ = ["get_access_request_dao", "get_dataset_dao"]


async def get_access_request_dao(
    *, dao_factory: DaoFactoryProtocol
) -> AccessRequestDaoPort:
    """Get an Access Request DAO."""
    return await dao_factory.get_dao(
        name="accessRequests",
        dto_model=models.AccessRequest,
        id_field="id",
    )


async def get_dataset_dao(*, dao_factory: DaoFactoryProtocol) -> DatasetDaoPort:
    """Get a Dataset DAO."""
    return await dao_factory.get_dao(
        name="datasets",
        dto_model=models.Dataset,
        id_field="id",
    )
