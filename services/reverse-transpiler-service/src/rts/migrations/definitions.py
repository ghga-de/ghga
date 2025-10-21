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

"""Database migration logic for the RTS."""

from contextlib import suppress

from gridfs import AsyncGridFSBucket, NoFile
from hexkit.providers.mongodb.migrations import MigrationDefinition, Reversible

from rts.adapters.outbound.dao import GridFSDaoFactory
from rts.models import StudyMetadata

METADATA = "metadata"
WORKBOOKS = "workbooks"


class V2Migration(MigrationDefinition, Reversible):
    """Move the contents of the study metadata collection ("metadata") into GridFS.

    This can be reversed by removing the data from GridFS and storing it back into a
    collection with the original name ("metadata").
    """

    version = 2

    async def apply(self):
        """Perform the migration."""
        # Move all existing workbook files from default 'fs' bucket into 'workbooks' bucket
        default_bucket = AsyncGridFSBucket(self._db)
        workbooks_bucket = AsyncGridFSBucket(self._db, bucket_name=WORKBOOKS)
        async for file in default_bucket.find():
            await workbooks_bucket.upload_from_stream_with_id(
                file_id=file._id,
                filename=file.filename,
                source=file,
            )
            await default_bucket.delete(file._id)

        # Iterate over the collection and move each item into GridFS
        collection = self._db[METADATA]
        metadata_bucket = AsyncGridFSBucket(db=self._db, bucket_name=METADATA)
        async for doc in collection.find():
            doc["study_accession"] = doc.pop("_id")
            metadata = StudyMetadata(**doc)
            accession = metadata.study_accession

            # We don't want to accidentally overwrite something in this process,
            #  so be careful and double check there's no name collision:
            with suppress(NoFile):
                async for _ in metadata_bucket.find({"filename": accession}):
                    raise RuntimeError(f"Unexpected name collision for {accession}")
            await metadata_bucket.upload_from_stream_with_id(
                file_id=accession,
                filename=accession,
                source=metadata.model_dump_json().encode("utf-8"),
            )
        await collection.drop()

    async def unapply(self):
        """Reverse the migration"""
        collection = self._db[METADATA]
        gridfs_dao_factory = GridFSDaoFactory(db=self._db)
        gridfs_dao = gridfs_dao_factory.get_metadata_dao()
        async for metadata in gridfs_dao.find_all():
            doc = metadata.model_dump()
            doc["_id"] = doc.pop("study_accession")
            await collection.insert_one(doc)
            await gridfs_dao.delete(filename=doc["_id"])

        # Move workbooks back into default 'fs' bucket
        default_bucket = AsyncGridFSBucket(self._db)
        workbooks_bucket = AsyncGridFSBucket(self._db, bucket_name=WORKBOOKS)
        async for file in workbooks_bucket.find():
            await default_bucket.upload_from_stream_with_id(
                file_id=file._id,
                filename=file.filename,
                source=file,
            )
            await workbooks_bucket.delete(file._id)
