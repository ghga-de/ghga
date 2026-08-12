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

"""V3 Migration"""

from typing import cast

from hexkit.providers.mongodb.migrations import (
    Document,
    MigrationDefinition,
    Reversible,
)
from wps.config import Config
from wps.core.models import Dataset


class V3Migration(MigrationDefinition, Reversible):
    """Rename DatasetFile.id to DatasetFile.accession in the datasets collection.

    Affected collections:
    - datasets (Dataset)
        - files[*].id -> files[*].accession
    """

    version = 3

    async def apply(self):
        """Perform the migration."""
        config = Config()
        datasets_collection = config.datasets_collection

        async def rename_id_to_accession(doc: Document) -> Document:
            updated_files = []
            for file in doc["files"]:
                file = cast(dict, file)  # for type-checking

                # Transform old DatasetFile objects in an idempotent manner
                updated_file = None
                if file.keys() == {"id", "extension"}:
                    updated_file = {
                        "accession": file["id"],
                        "extension": file["extension"],
                    }
                elif file.keys() != {"accession", "extension"}:
                    raise ValueError(
                        "Unexpected DatasetFile schema detected in Dataset"
                        + f" ID {doc['_id']}. Expected each file to have keys 'id' and"
                        + " 'extension' in old docs and 'accession' and 'extension' in"
                        + " migrated docs."
                    )
                updated_files.append(updated_file or file)
            doc["files"] = updated_files
            return doc

        async with self.auto_finalize(
            coll_names=[datasets_collection], copy_indexes=True
        ):
            await self.migrate_docs_in_collection(
                coll_name=datasets_collection,
                change_function=rename_id_to_accession,
                validation_model=Dataset,
                id_field="id",
            )

    async def unapply(self):
        """Revert the migration."""
        config = Config()
        datasets_collection = config.datasets_collection

        async def rename_accession_to_id(doc: Document) -> Document:
            doc["files"] = [
                {"id": file["accession"], "extension": file["extension"]}
                for file in doc["files"]
            ]
            return doc

        async with self.auto_finalize(
            coll_names=[datasets_collection], copy_indexes=True
        ):
            await self.migrate_docs_in_collection(
                coll_name=datasets_collection,
                change_function=rename_accession_to_id,
            )
