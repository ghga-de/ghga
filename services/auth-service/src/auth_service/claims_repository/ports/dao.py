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

"""DAOs that are used as part of the outbound port for the auth service."""

from abc import ABC, abstractmethod
from typing import TypeAlias

from hexkit.protocols.dao import Dao

from ..models.claims import Claim as ClaimDto

__all__ = ["ClaimDao", "ClaimDaoFactoryPort"]


ClaimDao: TypeAlias = Dao[ClaimDto]


class ClaimDaoFactoryPort(ABC):
    """Port that provides a factory for user claims data access objects."""

    @abstractmethod
    async def get_claim_dao(self) -> ClaimDao:
        """Construct a DAO for interacting with user claims in a database."""
        ...
