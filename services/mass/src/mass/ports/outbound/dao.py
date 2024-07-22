# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""ResourceDao Port and DaoCollectionPort"""

from abc import ABC, abstractmethod
from typing import TypeAlias

from hexkit.protocols.dao import DaoNaturalId

from mass.core.models import Resource

ResourceDao: TypeAlias = DaoNaturalId[Resource]


class DaoCollectionPort(ABC):
    """Port for a DAO collection object"""

    @abstractmethod
    def get_dao(self, *, class_name: str) -> ResourceDao:
        """Retrieve a ResourceDaoPort for the specified resource class name

        Args:
            class_name (str): name of the resource class

        Returns:
            A DAO for the specified resource (ResourceDaoPort)
        """
        ...

    def create_collections_and_indexes_if_needed(self) -> None:  # noqa: B027
        """Creates `MongoDB` collections and indexes.

        Creates collections for all configured classes in `searchable_classes` if they don't
        already exist. At the same time, it will also create the text index if it doesn't
        already exist. This is primarily needed because the text index has to exist in order
        to perform query string searches.
        """
        ...

    def recreate_collections_and_indexes(self) -> None:  # noqa: B027
        """Recreates `MongoDB` collections and indexes.

        Recreates collections and indexes even if they have already been created. This may
        happen when the database has been modified from the outside, e.g. for testing.
        """
        ...
