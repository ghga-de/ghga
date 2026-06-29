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

"""Port definition for the LegacyResourceManager.

LEGACY: This port (and its implementation) exist only to consume the "searchable
resources" emitted by the metldata producer. Once this service becomes the
source of truth for studies and experimental metadata - which are the origin of these
searchable resources - metldata and this consumer become obsolete and can be removed.
"""

from abc import ABC, abstractmethod

import ghga_event_schemas.pydantic_ as event_schemas


class LegacyResourceManagerPort(ABC):
    """Port for handling searchable resources from the metldata producer.

    A resource is uniquely identified by the ``(class_name, accession)`` pair.
    """

    @abstractmethod
    async def upsert_resource(
        self, *, resource: event_schemas.SearchableResource
    ) -> None:
        """Handle an upserted searchable resource.

        Extracts the embedded Study from the resource content (if any) and inserts it
        into the existing study DAO if not already known. Studies are only created
        through this mechanism, never updated.
        """
        ...

    @abstractmethod
    async def delete_resource(
        self, *, resource_info: event_schemas.SearchableResourceInfo
    ) -> None:
        """Handle a deleted searchable resource.

        The eventual job of this method is to remove the corresponding Study from the
        existing study DAO. Currently only a stub (see implementation).
        """
        ...
