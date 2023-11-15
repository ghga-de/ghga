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

"""Translation between general and claims specific DAOs."""

from hexkit.protocols.dao import DaoFactoryProtocol
from pydantic_settings import BaseSettings

from ..models.dto import Claim as ClaimDto
from ..models.dto import ClaimFullCreation as ClaimCreationDto
from ..ports.dao import ClaimDao, ClaimDaoFactoryPort

__all__ = ["ClaimDaoFactory", "ClaimDaoFactoryConfig"]


class ClaimDaoFactoryConfig(BaseSettings):
    """User claims DAO factory config parameters and their defaults."""

    collection_name: str = "claims"


class ClaimDaoFactory(ClaimDaoFactoryPort):
    """Translation between ClaimsDaoFactoryPort and DaoFactoryProtocol."""

    def __init__(
        self, *, config: ClaimDaoFactoryConfig, dao_factory: DaoFactoryProtocol
    ) -> None:
        """Configure with provider for the the DaoFactoryProtocol"""
        self._collection_name = config.collection_name
        self._dao_factory = dao_factory

    async def get_claim_dao(self) -> ClaimDao:
        """Construct a DAO for interacting with user claims data in a database."""
        return await self._dao_factory.get_dao(
            name=self._collection_name,
            dto_model=ClaimDto,
            id_field="id",
            dto_creation_model=ClaimCreationDto,
            # fields_to_index=["user_id", "visa_type"], #  not yet supported
        )
