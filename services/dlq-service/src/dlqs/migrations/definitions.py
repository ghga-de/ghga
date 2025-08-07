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

"""Database migration logic for DLQS"""

from hexkit.providers.mongodb.migrations import (
    Document,
    MigrationDefinition,
    Reversible,
)
from hexkit.providers.mongodb.migrations.helpers import convert_uuids_and_datetimes_v6

from dlqs.models import StoredDLQEvent

DLQ_EVENTS_COLLECTION = "dlqEvents"


class V2Migration(MigrationDefinition, Reversible):
    """Update the stored data to have native-typed UUIDs and datetimes and switch
    to new event structure:
    - convert _id to UUID
    - convert timestamp to datetime
    - populate dlq_info.original_event_id with None
    - delete dlq_info.partition and offset

    This cannot be fully reversed as some data is permanently lost (offset, partition).
    """

    version = 2

    async def apply(self):
        """Perform the migration."""
        convert_field_types = convert_uuids_and_datetimes_v6(
            uuid_fields=["_id"], date_fields=["timestamp"]
        )

        async def change_doc(doc: Document) -> Document:
            """Make all doc changes"""
            doc = await convert_field_types(doc)
            del doc["dlq_info"]["partition"]
            del doc["dlq_info"]["offset"]
            doc["dlq_info"]["original_event_id"] = None
            return doc

        async with self.auto_finalize(DLQ_EVENTS_COLLECTION, copy_indexes=True):
            await self.migrate_docs_in_collection(
                coll_name=DLQ_EVENTS_COLLECTION,
                change_function=change_doc,
                validation_model=StoredDLQEvent,
                id_field="dlq_id",
            )

    async def unapply(self):
        """Reverse the migration."""

        async def revert_doc(doc: Document) -> Document:
            """Revert all doc changes. This will populate partition and offset as 0."""
            doc["dlq_info"]["partition"] = 0
            doc["dlq_info"]["offset"] = 0
            del doc["dlq_info"]["original_event_id"]
            doc["_id"] = str(doc["_id"])
            doc["timestamp"] = doc["timestamp"].isoformat()
            return doc

        async with self.auto_finalize(DLQ_EVENTS_COLLECTION, copy_indexes=True):
            await self.migrate_docs_in_collection(
                coll_name=DLQ_EVENTS_COLLECTION,
                change_function=revert_doc,
            )
