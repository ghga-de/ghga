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

"""Database migration logic for FIS"""

import logging
from uuid import uuid4

from hexkit.providers.mongodb.migrations import (
    Document,
    MigrationDefinition,
    Reversible,
    validate_doc,
)
from hexkit.providers.mongodb.migrations.helpers import (
    convert_persistent_event_v6,
    convert_uuids_and_datetimes_v6,
)
from hexkit.providers.mongokafka.provider.persistent_pub import PersistentKafkaEvent

from fis.config import Config

log = logging.getLogger(__name__)

# Collection names defined as constants
FIS_PERSISTED_EVENTS = "fisPersistedEvents"
INGESTED_FILES = "ingestedFiles"


class V2Migration(MigrationDefinition):
    """Move stored outbox events from the `file-validations` to two new collections:

    1. `ingestedFiles`: where each document merely contains the file ID
    2. `fisPersistedEvents`: a collection used for event persistence (replaces outbox)

    This migration is not reversible because it would require writing migrations for
    most other file services only for the purpose of making them reversible too.
    """

    version = 2

    async def apply(self):
        """Perform the migration."""
        config = Config()
        outbox_collection_name = config.file_validations_collection
        file_validations_collection = self._db[outbox_collection_name]
        ingested_files_collection = self._db[INGESTED_FILES]
        persisted_events_collection = self._db[FIS_PERSISTED_EVENTS]

        topic = config.file_interrogations_topic
        type_ = config.interrogation_success_type

        # Get the file ID and metadata from the outbox events
        async for doc in file_validations_collection.find():
            file_id = doc.pop("_id")
            doc["file_id"] = file_id
            outbox_metadata = doc.pop("__metadata__", {})
            persistent_event = {
                "_id": f"{topic}:{file_id}",
                "topic": topic,
                "type_": type_,
                "payload": doc,
                "key": file_id,
                "headers": {},
                "correlation_id": outbox_metadata.get("correlation_id"),
                "created": doc["upload_date"].replace("+00:00", "Z"),
                "published": outbox_metadata.get("published"),
            }

            # Validate the persistent event
            validate_doc(
                {**persistent_event}, model=PersistentKafkaEvent, id_field="id"
            )

            # Insert records into the v2 collections
            await ingested_files_collection.insert_one({"_id": file_id})
            await persisted_events_collection.insert_one(persistent_event)

        # Drop the old outbox events collection
        await file_validations_collection.drop()


class V3Migration(MigrationDefinition, Reversible):
    """Store UUID and datetime fields as actual UUIDs and datetimes in the DB.

    Touches only the `fisPersistedEvents` collection:
    - update `created`, `correlation_id`, and populate `event_id`
    - in the payload field, update `object_id` and `upload_date`

    This can be reversed by converting the UUIDs and datetimes back to strings.
    """

    version = 3

    async def apply(self):
        """Perform the migration"""
        convert_file_registered = convert_uuids_and_datetimes_v6(
            uuid_fields=["object_id"], date_fields=["upload_date"]
        )

        async def convert_persisted_event(doc: Document) -> Document:
            # Convert the common event fields with hexkit's utility function
            doc = await convert_persistent_event_v6(doc)
            if doc["correlation_id"].version != 4:
                new_cid = uuid4()
                log.info(
                    "Replaced bad correlation ID %s with new one: %s",
                    doc["correlation_id"],
                    new_cid,
                )
                doc["correlation_id"] = new_cid

            # convert the remaining fields inside the payload, treat payload as subdoc
            payload = doc["payload"]  # the field should always exist, raise if not
            payload = await convert_file_registered(payload)
            doc["payload"] = payload
            return doc

        async with self.auto_finalize(
            coll_names=FIS_PERSISTED_EVENTS, copy_indexes=True
        ):
            await self.migrate_docs_in_collection(
                coll_name=FIS_PERSISTED_EVENTS,
                change_function=convert_persisted_event,
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

            payload = doc["payload"]
            payload["object_id"] = str(payload["object_id"])
            payload["upload_date"] = payload["upload_date"].isoformat()
            doc["payload"] = payload
            return doc

        async with self.auto_finalize(
            coll_names=FIS_PERSISTED_EVENTS, copy_indexes=True
        ):
            # Don't provide validation models here
            await self.migrate_docs_in_collection(
                coll_name=FIS_PERSISTED_EVENTS,
                change_function=revert_persistent_event,
            )
