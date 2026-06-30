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

"""Database migration logic for the rs service."""

import logging

from hexkit.providers.mongodb.migrations import (
    Document,
    MigrationDefinition,
    Reversible,
)
from hexkit.utils import now_utc_ms_prec

from rs.constants import FILE_ACCESSION_COLLECTION, RESEARCH_DATA_UPLOAD_BOX_COLLECTION
from rs.core.models import FileAccession

log = logging.getLogger(__name__)

# The pre-migration collection names (the new names are FILE_ACCESSION_COLLECTION
# and RESEARCH_DATA_UPLOAD_BOX_COLLECTION respectively).
V1_FILE_ACCESSION_MAPPING_COLLECTION = "fileAccessionMappings"
V1_BOX_COLLECTION = "boxes"


class V2Migration(MigrationDefinition, Reversible):
    """Rename and reshape the file-accession and box collections.

    1. Replace the `fileAccessionMappings` collection with `fileAccessions`.

       The old collection stored `FileAccessionMapping` outbox documents keyed by
       the accession string (`_id`) with a `file_id`. The new collection stores the
       richer `FileAccession` model, able to also track unmapped accessions and
       studies. For each existing (already-mapped) document:
       - `_id` (the accession) is kept and becomes the new `pid`
       - `file_id` is carried over
       - `study_id` is set to None (unknown for legacy records)
       - `created` and `mapped` are set to the migration run time
       - the outbox `__metadata__` is preserved (publication state is retained)

    2. Rename the `boxes` collection to `researchDataUploadBoxes`.

       The collection stores `ResearchDataUploadBox` outbox documents. Only the
       collection name changes; the document schema is unchanged, so the collection
       is renamed atomically (each document, including its `_id` and outbox
       `__metadata__`, is preserved verbatim).

    The migration is crash-safe: the reshaped file accessions are built in a
    temporary collection and the boxes are renamed atomically, with the final swap
    into place happening only at the end. The legacy `fileAccessionMappings` and
    `boxes` collections no longer exist once the migration completes. An interrupted
    run leaves the source collections intact and can simply be retried.

    Reversal is best-effort: the box rename is fully reversible, but the file
    accession reversal only recovers the original `FileAccessionMapping` fields
    (`_id` and `file_id`). The backfilled `created`/`mapped` timestamps and the
    `study_id` are dropped, and unmapped accessions (those with a null `file_id`,
    which had no representation in the old schema) are discarded.
    """

    version = 2

    async def apply(self):
        """Perform the migration."""
        collection_names = await self._db.list_collection_names()

        await self._migrate_file_accessions(collection_names)
        await self._migrate_boxes(collection_names)

    async def unapply(self):
        """Reverse the migration (best-effort)."""
        collection_names = await self._db.list_collection_names()

        await self._unmigrate_file_accessions(collection_names)
        await self._unmigrate_boxes(collection_names)

    async def _migrate_file_accessions(self, collection_names: list[str]):
        """Replace the `fileAccessionMappings` collection with `fileAccessions`."""
        if V1_FILE_ACCESSION_MAPPING_COLLECTION not in collection_names:
            log.info(
                "Collection '%s' not found, nothing to migrate %s",
                V1_FILE_ACCESSION_MAPPING_COLLECTION,
                self._log_blurb,
            )
            return

        now = now_utc_ms_prec()

        async def to_file_accession(doc: Document) -> Document:
            """Reshape a legacy `FileAccessionMapping` doc into a `FileAccession`."""
            metadata = doc.get("__metadata__")
            file_accession = FileAccession(
                pid=doc["_id"],
                file_id=doc.get("file_id"),
                study_id=None,
                created=now,
                mapped=now,
            )
            new_doc = file_accession.model_dump()
            new_doc["_id"] = new_doc.pop("pid")
            new_doc["__metadata__"] = metadata or {
                "deleted": False,
                "published": True,
                "correlation_id": "",
                "last_event_id": None,
            }
            return new_doc

        # Build the reshaped documents in a temporary collection. This leaves the
        # source collection untouched and drops the temp collection first, so an
        # interrupted run can simply be retried without hitting duplicate IDs.
        # No `validation_model` is passed: the docs carry an outbox `__metadata__`
        # envelope that `validate_doc` would reject as an unexpected field.
        await self.migrate_docs_in_collection(
            coll_name=V1_FILE_ACCESSION_MAPPING_COLLECTION,
            change_function=to_file_accession,
        )

        # Atomically move the reshaped collection into its final name, then drop the
        # source. `dropTarget` keeps the rename idempotent across retries. The temp
        # collection is absent only if the source held no documents.
        temp_name = self.new_temp_name(V1_FILE_ACCESSION_MAPPING_COLLECTION)
        if temp_name in await self._db.list_collection_names():
            await self._db[temp_name].rename(FILE_ACCESSION_COLLECTION, dropTarget=True)
        await self._db[V1_FILE_ACCESSION_MAPPING_COLLECTION].drop()

        log.info(
            "Migrated collection '%s' to '%s' %s",
            V1_FILE_ACCESSION_MAPPING_COLLECTION,
            FILE_ACCESSION_COLLECTION,
            self._log_blurb,
        )

    async def _migrate_boxes(self, collection_names: list[str]):
        """Rename the `boxes` collection to `researchDataUploadBoxes`."""
        if V1_BOX_COLLECTION not in collection_names:
            log.info(
                "Collection '%s' not found, nothing to migrate %s",
                V1_BOX_COLLECTION,
                self._log_blurb,
            )
            return

        # The documents are copied verbatim, so a single atomic rename suffices.
        # There is no intermediate state, which makes this inherently crash-safe.
        # `dropTarget` keeps the rename idempotent across retries.
        await self._db[V1_BOX_COLLECTION].rename(
            RESEARCH_DATA_UPLOAD_BOX_COLLECTION, dropTarget=True
        )

        log.info(
            "Migrated collection '%s' to '%s' %s",
            V1_BOX_COLLECTION,
            RESEARCH_DATA_UPLOAD_BOX_COLLECTION,
            self._log_blurb,
        )

    async def _unmigrate_file_accessions(self, collection_names: list[str]):
        """Restore the `fileAccessionMappings` collection from `fileAccessions`.

        Only the original `FileAccessionMapping` fields (`_id` and `file_id`) are
        recovered; `study_id`, `created` and `mapped` are dropped. Unmapped
        accessions (with a null `file_id`) had no representation in the old schema
        and are discarded.
        """
        if FILE_ACCESSION_COLLECTION not in collection_names:
            log.info(
                "Collection '%s' not found, nothing to migrate %s",
                FILE_ACCESSION_COLLECTION,
                self._log_blurb,
            )
            return

        new_collection = self._db[FILE_ACCESSION_COLLECTION]

        # Build the restored documents in a temporary collection, dropping it first so
        # an interrupted run can be retried. `migrate_docs_in_collection` can't be used
        # here because unmapped accessions (null `file_id`) have to be filtered out.
        temp_name = self.new_temp_name(V1_FILE_ACCESSION_MAPPING_COLLECTION)
        await self._db.drop_collection(temp_name)
        temp_collection = self._db[temp_name]

        async for doc in new_collection.find():
            if doc.get("file_id") is None:
                continue
            old_doc: Document = {"_id": doc["_id"], "file_id": doc["file_id"]}
            metadata = doc.get("__metadata__")
            if metadata is not None:
                old_doc["__metadata__"] = metadata
            await temp_collection.insert_one(old_doc)

        # Atomically move the restored collection into place, then drop the source.
        # The temp collection is absent only if nothing was restored.
        if temp_name in await self._db.list_collection_names():
            await self._db[temp_name].rename(
                V1_FILE_ACCESSION_MAPPING_COLLECTION, dropTarget=True
            )
        await new_collection.drop()

        log.info(
            "Reverted collection '%s' to '%s' %s",
            FILE_ACCESSION_COLLECTION,
            V1_FILE_ACCESSION_MAPPING_COLLECTION,
            self._log_blurb,
        )

    async def _unmigrate_boxes(self, collection_names: list[str]):
        """Rename the `researchDataUploadBoxes` collection back to `boxes`."""
        if RESEARCH_DATA_UPLOAD_BOX_COLLECTION not in collection_names:
            log.info(
                "Collection '%s' not found, nothing to migrate %s",
                RESEARCH_DATA_UPLOAD_BOX_COLLECTION,
                self._log_blurb,
            )
            return

        # The documents are unchanged, so a single atomic rename suffices.
        await self._db[RESEARCH_DATA_UPLOAD_BOX_COLLECTION].rename(
            V1_BOX_COLLECTION, dropTarget=True
        )

        log.info(
            "Reverted collection '%s' to '%s' %s",
            RESEARCH_DATA_UPLOAD_BOX_COLLECTION,
            V1_BOX_COLLECTION,
            self._log_blurb,
        )
