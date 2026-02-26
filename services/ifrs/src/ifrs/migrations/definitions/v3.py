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

from contextlib import suppress
from hashlib import sha256
from uuid import UUID

from hexkit.providers.mongodb.migrations import Document, MigrationDefinition
from hexkit.providers.mongokafka.provider.persistent_pub import PersistentKafkaEvent

from ifrs.core.models import FileMetadata

# Collection names defined as constants
IFRS_PERSISTED_EVENTS = "ifrsPersistedEvents"
FILE_METADATA = "file_metadata"


def derive_file_id_from_accession(accession: str) -> UUID:
    """Use the first portion of the SHA256 hash of an accession to derive a UUID4"""
    hash = sha256(accession.encode()).hexdigest()
    uuid_str = f"{hash[0:8]}-{hash[8:12]}-4{hash[13:16]}-a{hash[17:20]}-{hash[20:32]}"
    return UUID(uuid_str)


async def update_file_metadata(doc: Document) -> Document:
    """Update file metadata, skipping already updated docs.

    If a doc has the `archive_date` field, it has already been updated.
    """
    if "archive_date" in doc:
        return doc

    doc["_id"] = derive_file_id_from_accession(doc["_id"])
    doc["archive_date"] = doc.pop("upload_date")
    doc["secret_id"] = doc.pop("decryption_secret_id")
    doc["part_size"] = doc.pop("encrypted_part_size")
    doc["encrypted_size"] = doc.pop("object_size")
    del doc["content_offset"]
    return doc


async def update_event(doc: Document) -> Document:
    """Convert a persistent event payloads for FileInternallyRegistered events
    and FileDeleted events.
    """
    # Both persisted event types used the file accession as the key, so if the key now
    #  contains a UUID4, then we can assume the doc is already up to date
    with suppress(ValueError):
        _ = UUID(doc["key"])
        return doc

    # payload points to doc["payload"], so no need to reassign the payload field
    payload = doc["payload"]

    # Both event types have file_id in the payload, so update that first
    uuid4_file_id = derive_file_id_from_accession(payload["file_id"])
    payload["file_id"] = uuid4_file_id

    # Use the updated file_id to update the event key and the compaction_key field (_id)
    doc["_id"] = doc["_id"].replace(doc["key"], str(uuid4_file_id))
    doc["key"] = str(uuid4_file_id)
    doc["published"] = False

    # If the only payload key is file_id, it's a FileDeleted event - we're already done.
    if list(payload) == ["file_id"]:
        return doc

    # FileInternallyRegistered events only:
    payload["archive_date"] = payload.pop("upload_date")
    payload["storage_alias"] = payload.pop("s3_endpoint_alias")
    payload["secret_id"] = payload.pop("decryption_secret_id")
    payload["part_size"] = payload.pop("encrypted_part_size")
    del payload["content_offset"]

    return doc


class V3Migration(MigrationDefinition):
    """Migrate select fields in the IFRS's database for the Sarcastic Fringehead epic.

    Affected data:
    - `file_metadata` collection:
      - Fields affected:
        - `_id`: value replace with file ID derived from accession
        - `upload_date`: renamed to `archive_date`
        - `decryption_secret_id`: renamed to `secret_id`
        - `encrypted_part_size`: renamed to `part_size`
        - `object_size`: renamed to `encrypted_size`
        - `content_offset`: removed

    - `ifrsPersistedEvents` collection:
      - The following are affected for all docs (FileDeleted and FileInternallyRegistered):
        - `_id`: if value contains accession, accession is replaced by derived file ID
        - `key`: accession replaced by derived file ID
        - `published`: Set to False
        - `payload.file_id`: value replaced with file ID derived from accession
      - The following are only for the FileInternallyRegistered events:
        - `payload.upload_date`: renamed to `payload.archive_date`
        - `payload.s3_endpoint_alias`: renamed to `payload.storage_alias`
        - `payload.decryption_secret_id`: renamed to `payload.secret_id`
        - `payload.encrypted_part_size`: renamed to `payload.part_size`
        - `payload.content_offset`: deleted

    This migration cannot be reversed because the accession-UUID4 conversion is one-way.
    """

    version = 3

    async def apply(self):
        """Perform the migration"""
        async with self.auto_finalize(
            coll_names=[FILE_METADATA, IFRS_PERSISTED_EVENTS], copy_indexes=False
        ):
            # migrate the file metadata collection
            await self.migrate_docs_in_collection(
                coll_name=FILE_METADATA,
                change_function=update_file_metadata,
                validation_model=FileMetadata,
                id_field="id",
            )
            # migrate persistent events and their payload fields
            await self.migrate_docs_in_collection(
                coll_name=IFRS_PERSISTED_EVENTS,
                change_function=update_event,
                validation_model=PersistentKafkaEvent,
                id_field="compaction_key",
            )
