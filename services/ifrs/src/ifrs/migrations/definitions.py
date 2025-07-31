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

"""Database migration logic for IFRS"""

from hexkit.providers.mongodb.migrations import (
    Document,
    MigrationDefinition,
    Reversible,
)
from hexkit.providers.mongodb.migrations.helpers import (
    convert_persistent_event_v6,
    convert_uuids_and_datetimes_v6,
)
from hexkit.providers.mongokafka.provider.persistent_pub import PersistentKafkaEvent

from ifrs.core.models import FileMetadata

# Collection names defined as constants
IFRS_PERSISTED_EVENTS = "ifrsPersistedEvents"
FILE_METADATA = "file_metadata"


class V2Migration(MigrationDefinition, Reversible):
    """Migrate select fields in the IFRS's data base for hexkit v6.

    Affected data:
    - `file_metadata` collection:
      - Fields affected:
        - `object_id`: *str* -> *UUID4*
        - `upload_date`: *str* -> *datetime*

    - `ifrsPersistedEvents` collection:
      - Fields affected:
        - `created`: *str* -> *datetime*
        - `correlation_id`: *str* -> *UUID4*
        - `event_id`: new, *UUID4*
        - `payload.object_id`: *str* -> *UUID4*
        - `payload.upload_date`: *str* -> *datetime*

    Event payload changes are required for the FileInternallyRegistered topic,
    affecting `object_id` and `upload_date`.

    This can be reversed by converting the UUIDs and datetimes back to strings.
    """

    version = 2

    async def apply(self):
        """Perform the migration"""
        convert_file_metadata = convert_uuids_and_datetimes_v6(
            uuid_fields=["object_id"], date_fields=["upload_date"]
        )

        async def convert_event(doc: Document) -> Document:
            """Convert a persistent event and its payload."""
            doc = await convert_persistent_event_v6(doc)

            # The only payloads to migrate are ones that have object id
            if "object_id" in doc["payload"]:
                doc["payload"] = await convert_file_metadata(doc["payload"])

            return doc

        async with self.auto_finalize(
            coll_names=[FILE_METADATA, IFRS_PERSISTED_EVENTS], copy_indexes=True
        ):
            # migrate the file metadata collection
            await self.migrate_docs_in_collection(
                coll_name=FILE_METADATA,
                change_function=convert_file_metadata,
                validation_model=FileMetadata,
                id_field="file_id",
            )
            # migrate persistent events and their payload fields
            await self.migrate_docs_in_collection(
                coll_name=IFRS_PERSISTED_EVENTS,
                change_function=convert_event,
                validation_model=PersistentKafkaEvent,
                id_field="compaction_key",
            )

    async def unapply(self):
        """Reverse the migration"""

        async def revert_file_metadata(doc: Document) -> Document:
            """Convert object_id and upload_date to strings again.

            Used on its own to migrate file_metadata, and as a helper in
            migrating persistent events.
            """
            doc["object_id"] = str(doc["object_id"])
            doc["upload_date"] = doc["upload_date"].isoformat()
            return doc

        async def revert_persistent_event(doc: Document) -> Document:
            """Convert the fields back into strings"""
            doc.pop("event_id")
            doc["correlation_id"] = str(doc["correlation_id"])
            doc["created"] = doc["created"].isoformat()

            if "object_id" in doc["payload"]:
                doc["payload"] = await revert_file_metadata(doc["payload"])
            return doc

        async with self.auto_finalize(
            coll_names=[FILE_METADATA, IFRS_PERSISTED_EVENTS], copy_indexes=True
        ):
            # Revert file metadata collection
            await self.migrate_docs_in_collection(
                coll_name=FILE_METADATA,
                change_function=revert_file_metadata,
            )

            # Revert persistent events
            await self.migrate_docs_in_collection(
                coll_name=IFRS_PERSISTED_EVENTS,
                change_function=revert_persistent_event,
            )
