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

"""Database migration logic for DCS"""

from uuid import UUID

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

from dcs.core.models import AccessTimeDrsObject

DRS_OBJECTS = "drs_objects"
DCS_PERSISTED_EVENTS = "dcsPersistedEvents"


class V2Migration(MigrationDefinition, Reversible):
    """Update the stored data to have native-typed UUIDs and datetimes.

    Affected collections:
    - drs_objects (AccessTimeDrsObject)
        - object_id, creation_date, and last_accessed
    - dcsPersistedEvents

    This can be reversed by converting the UUIDs and datetimes back to strings.
    """

    version = 2

    _drs_dates: list[str] = ["creation_date", "last_accessed"]

    async def apply(self):
        """Perform the migration."""
        convert_drs_objects = convert_uuids_and_datetimes_v6(
            uuid_fields=["object_id"], date_fields=self._drs_dates
        )

        convert_file_registered = convert_uuids_and_datetimes_v6(
            date_fields=["upload_date"]
        )

        async def convert_persisted_events(doc: Document) -> Document:
            # Convert the common event fields with hexkit's utility function
            doc = await convert_persistent_event_v6(doc)

            # convert the remaining fields inside the payload, treat payload as subdoc
            payload = doc["payload"]  # the field should always exist, raise if not
            if object_id := payload.get("object_id"):
                payload["object_id"] = UUID(object_id)
            if "upload_date" in payload:
                payload = await convert_file_registered(payload)
            doc["payload"] = payload
            return doc

        async with self.auto_finalize(
            coll_names=[DRS_OBJECTS, DCS_PERSISTED_EVENTS], copy_indexes=True
        ):
            await self.migrate_docs_in_collection(
                coll_name=DRS_OBJECTS,
                change_function=convert_drs_objects,
                validation_model=AccessTimeDrsObject,
                id_field="file_id",
            )

            await self.migrate_docs_in_collection(
                coll_name=DCS_PERSISTED_EVENTS,
                change_function=convert_persisted_events,
                validation_model=PersistentKafkaEvent,
                id_field="compaction_key",
            )

    async def unapply(self):
        """Revert the migration."""

        # define the change function
        async def revert_drs_objects(doc: Document) -> Document:
            """Convert the fields back into strings"""
            doc["object_id"] = str(doc["object_id"])
            for field in self._drs_dates:
                doc[field] = doc[field].isoformat()
            return doc

        async def revert_persistent_event(doc: Document) -> Document:
            """Convert the fields back into strings"""
            doc.pop("event_id")
            doc["correlation_id"] = str(doc["correlation_id"])
            doc["created"] = doc["created"].isoformat()

            payload = doc["payload"]
            if object_id := payload.get("object_id"):
                payload["object_id"] = str(object_id)
            if upload_date := payload.get("upload_date"):
                payload["upload_date"] = upload_date.isoformat()
            doc["payload"] = payload
            return doc

        async with self.auto_finalize(
            coll_names=[DRS_OBJECTS, DCS_PERSISTED_EVENTS], copy_indexes=True
        ):
            # Don't provide validation models here
            await self.migrate_docs_in_collection(
                coll_name=DRS_OBJECTS,
                change_function=revert_drs_objects,
            )
            await self.migrate_docs_in_collection(
                coll_name=DCS_PERSISTED_EVENTS,
                change_function=revert_persistent_event,
            )
