# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
"""Migration definitions for the IFRS"""

from ghga_service_commons.utils.multinode_storage import S3ObjectStorages

from ifrs.config import Config
from ifrs.core.models import FileMetadata
from ifrs.migration_logic import Document, MigrationDefinition, Reversible

METADATA_COLLECTION = "file_metadata"


class V2Migration(MigrationDefinition, Reversible):
    """Adds `object_size`"""

    version = 2

    def __init__(self, *args, **kwargs):
        """Initialize migration class and set up object storages to get object size"""
        super().__init__(*args, **kwargs)
        config = Config()
        self.storages = S3ObjectStorages(config=config)

    async def add_object_size(self, doc: Document) -> Document:
        """Populate the `object_size` field"""
        object_id = doc["object_id"]
        storage_alias = doc["storage_alias"]
        permanent_bucket_id, object_storage = self.storages.for_alias(storage_alias)
        doc["object_size"] = await object_storage.get_object_size(
            bucket_id=permanent_bucket_id, object_id=object_id
        )
        return doc

    async def remove_object_size(self, doc: Document) -> Document:
        """Remove the `object_size` field"""
        doc.pop("object_size", "")
        return doc

    async def apply(self):
        """Populate `object_size` field on docs in the file_metadata collection"""
        async with self.auto_finalize(METADATA_COLLECTION):
            await self.migrate_docs_in_collection(
                coll_name=METADATA_COLLECTION,
                change_function=self.add_object_size,
                validation_model=FileMetadata,
                id_field="file_id",
            )

    async def unapply(self):
        """Remove `object_size`"""
        async with self.auto_finalize(METADATA_COLLECTION):
            await self.migrate_docs_in_collection(
                coll_name=METADATA_COLLECTION,
                change_function=self.remove_object_size,
                validation_model=FileMetadata,
                id_field="file_id",
            )
