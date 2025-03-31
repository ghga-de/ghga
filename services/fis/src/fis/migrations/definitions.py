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

from hexkit.providers.mongodb.migrations import (
    MigrationDefinition,
    validate_doc,
)
from hexkit.providers.mongokafka.provider.persistent_pub import PersistentKafkaEvent

from fis.config import Config


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
        ingested_files_collection = self._db["ingestedFiles"]
        persisted_events_collection = self._db["fisPersistedEvents"]

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
