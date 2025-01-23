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
"""Migration definitions for the DCS"""

import math

import crypt4gh.lib

from dcs.core.models import AccessTimeDrsObject
from dcs.migration_logic import Document, MigrationDefinition, Reversible

DRS_OBJECT_COLLECTION = "drs_objects"


class V2Migration(MigrationDefinition, Reversible):
    """Adds `encrypted_size`"""

    version = 2

    async def add_encrypted_size(self, doc: Document) -> Document:
        """Populate the `encrypted_size` field"""
        decrypted_size = doc["decrypted_size"]

        # this calculation comes from the ds kit
        num_segments = math.ceil(decrypted_size / crypt4gh.lib.SEGMENT_SIZE)
        encrypted_size = decrypted_size + num_segments * 28
        doc["encrypted_size"] = encrypted_size
        return doc

    async def remove_encrypted_size(self, doc: Document) -> Document:
        """Remove the `encrypted_size` field"""
        doc.pop("encrypted_size", "")
        return doc

    async def apply(self):
        """Populate `encrypted_size` field on docs in the drs_objects collection"""
        async with self.auto_finalize(DRS_OBJECT_COLLECTION):
            await self.migrate_docs_in_collection(
                coll_name=DRS_OBJECT_COLLECTION,
                change_function=self.add_encrypted_size,
                validation_model=AccessTimeDrsObject,
                id_field="file_id",
            )

    async def unapply(self):
        """Remove `encrypted_size`"""
        async with self.auto_finalize(DRS_OBJECT_COLLECTION):
            await self.migrate_docs_in_collection(
                coll_name=DRS_OBJECT_COLLECTION,
                change_function=self.remove_encrypted_size,
                validation_model=AccessTimeDrsObject,
                id_field="file_id",
            )
