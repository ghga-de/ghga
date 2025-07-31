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

"""Database migration logic for PCS"""

from hexkit.providers.mongodb.migrations import (
    Document,
    MigrationDefinition,
    Reversible,
)
from hexkit.providers.mongodb.migrations.helpers import convert_persistent_event_v6
from hexkit.providers.mongokafka.provider.persistent_pub import PersistentKafkaEvent

# Collection names defined as constants
PCS_PERSISTED_EVENTS = "pcsPersistedEvents"


class V2Migration(MigrationDefinition, Reversible):
    """Migrate select fields in the `pcsPersistedEvents` collection for hexkit v6.

    Fields affected:
    - `created`: *str* -> *datetime*
    - `correlation_id`: *str* -> *UUID4*
    - `event_id`: new, *UUID4*

    No changes to payload, which only contains a string field.

    This can be reversed by converting the UUIDs and datetimes back to strings.
    """

    version = 2

    async def apply(self):
        """Perform the migration"""
        async with self.auto_finalize(
            coll_names=PCS_PERSISTED_EVENTS, copy_indexes=True
        ):
            await self.migrate_docs_in_collection(
                coll_name=PCS_PERSISTED_EVENTS,
                change_function=convert_persistent_event_v6,
                validation_model=PersistentKafkaEvent,
                id_field="compaction_key",
            )

    async def unapply(self):
        """Reverse the migration"""

        async def revert_persistent_event(doc: Document) -> Document:
            """Convert the fields back into strings"""
            doc.pop("event_id")
            doc["correlation_id"] = str(doc["correlation_id"])
            doc["created"] = doc["created"].isoformat()
            return doc

        async with self.auto_finalize(
            coll_names=PCS_PERSISTED_EVENTS, copy_indexes=True
        ):
            # Don't provide validation models here
            await self.migrate_docs_in_collection(
                coll_name=PCS_PERSISTED_EVENTS,
                change_function=revert_persistent_event,
            )
