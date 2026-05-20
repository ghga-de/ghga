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

"""Migration Definition for moving to DB version 3."""

from contextlib import suppress
from hashlib import sha256
from uuid import UUID

from hexkit.providers.mongodb.migrations import Document, MigrationDefinition
from hexkit.providers.mongokafka.provider.persistent_pub import PersistentKafkaEvent

from dcs.constants import DCS_PERSISTED_EVENTS_COLLECTION, DRS_OBJECTS_COLLECTION
from dcs.core.models import AccessTimeDrsObject


def derive_file_id_from_accession(accession: str) -> UUID:
    """Use the first portion of the SHA256 hash of an accession to derive a UUID4.

    This is the same algorithm used by IFRS, so the database values will be consistent
    across both services.
    """
    hashed_acc = sha256(accession.encode()).hexdigest()
    uuid_str = f"{hashed_acc[0:8]}-{hashed_acc[8:12]}-4{hashed_acc[13:16]}-a{hashed_acc[17:20]}-{hashed_acc[20:32]}"
    return UUID(uuid_str)


async def update_drs_object(doc: Document) -> Document:
    """Update a drs_objects document.

    If _id is already a UUID, the doc has been migrated; skip it.
    """
    if isinstance(doc["_id"], UUID):
        return doc

    doc["_id"] = derive_file_id_from_accession(doc["_id"])

    if "decryption_secret_id" in doc:
        doc["secret_id"] = doc.pop("decryption_secret_id")

    if "s3_endpoint_alias" in doc:
        doc["storage_alias"] = doc.pop("s3_endpoint_alias")

    return doc


async def update_event(doc: Document) -> Document:
    """Update a persisted event document.

    If doc["key"] is already a valid UUID, the doc has been migrated; skip it.
    Fields are updated field-by-field so this function handles any event type.
    """
    # For events, the idempotence check is done on the key because the _id is formatted
    #  like topic_name:event_key and it is therefore simpler to check the key. We cast
    #  to UUID instead of doing a UUID type-check because the key is actually a string
    with suppress(ValueError):
        _ = UUID(doc["key"])
        return doc

    payload = doc["payload"]

    uuid4_file_id = derive_file_id_from_accession(payload["file_id"])
    payload["file_id"] = uuid4_file_id

    doc["_id"] = f"{doc['topic']}:{uuid4_file_id}"
    doc["key"] = str(uuid4_file_id)
    doc["published"] = False

    # There are only two event types in the collection at this time:
    # FileDownloadServed event:
    if "target_object_id" in payload:
        payload["target_object_id"] = UUID(payload["target_object_id"])
        payload["storage_alias"] = payload.pop("s3_endpoint_alias")
    else:
        # FileRegisteredForDownload event:
        payload.pop("drs_uri")
        payload["archive_date"] = payload.pop("upload_date")

    return doc


class V3Migration(MigrationDefinition):
    """Migrate DCS database for the Sarcastic Fringehead epic.

    Affected data:
    - `drs_objects` collection:
      - `_id` (file_id): GHGA accession string converted to UUID4 via SHA256 hash
      - `decryption_secret_id`: renamed to `secret_id`
      - `s3_endpoint_alias`: renamed to `storage_alias`

    - `dcsPersistedEvents` collection:
      - `payload.file_id`: GHGA accession string converted to UUID4 via SHA256 hash
      - `key`: GHGA accession replaced by derived UUID4 (string)
      - `_id`: accession portion replaced by derived UUID4 (i.e. right of colon)
      - `published`: set to False to trigger republishing with updated payloads
      - `payload.s3_endpoint_alias`: renamed to `payload.storage_alias` (if present)
      - `payload.upload_date`: renamed to `payload.archive_date` (if present)
      - `payload.drs_uri`: removed (if present)

    This migration cannot be reversed because the accession-to-UUID4 conversion is one-way.
    """

    version = 3

    async def apply(self):
        """Perform the migration."""
        async with self.auto_finalize(
            coll_names=[DRS_OBJECTS_COLLECTION, DCS_PERSISTED_EVENTS_COLLECTION],
            copy_indexes=False,
        ):
            await self.migrate_docs_in_collection(
                coll_name=DRS_OBJECTS_COLLECTION,
                change_function=update_drs_object,
                validation_model=AccessTimeDrsObject,
                id_field="file_id",
            )
            await self.migrate_docs_in_collection(
                coll_name=DCS_PERSISTED_EVENTS_COLLECTION,
                change_function=update_event,
                validation_model=PersistentKafkaEvent,
                id_field="compaction_key",
            )
