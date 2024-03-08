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

"""DAOs that are used as part of the outbound port for the user management."""

from abc import ABC, abstractmethod

from hexkit.protocols.dao import DaoSurrogateId
from typing_extensions import TypeAlias  # in typing only since Python 3.10

from ..models.claims import Claim as ClaimDto
from ..models.claims import ClaimFullCreation as ClaimCreationDto

__all__ = ["ClaimDao", "ClaimDaoFactoryPort"]


ClaimDao: TypeAlias = DaoSurrogateId[ClaimDto, ClaimCreationDto]


class ClaimDaoFactoryPort(ABC):
    """Port that provides a factory for user claims data access objects."""

    @abstractmethod
    async def get_claim_dao(self) -> ClaimDao:
        """Construct a DAO for interacting with user claims in a database."""
        ...
