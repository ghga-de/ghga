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

"""Database migration logic for the WPS."""

from hexkit.providers.mongodb.migrations import (
    Document,
    MigrationDefinition,
    Reversible,
)
from hexkit.providers.mongodb.migrations.helpers import convert_uuids_and_datetimes_v6

from wps.core.models import WorkPackage

WORK_PACKAGES = "workPackages"


class V2Migration(MigrationDefinition, Reversible):
    """Update the stored data to have native-typed UUIDs and datetimes.
    Affected collections:
    - work_packages (WorkPackage)
        - id, created, and expires
    This can be reversed by converting the UUIDs and datetimes back to strings.
    """

    version = 2

    async def apply(self):
        """Perform the migration."""
        convert_work_packages = convert_uuids_and_datetimes_v6(
            uuid_fields=["_id", "user_id"], date_fields=["created", "expires"]
        )

        async with self.auto_finalize(coll_names=[WORK_PACKAGES], copy_indexes=True):
            await self.migrate_docs_in_collection(
                coll_name=WORK_PACKAGES,
                change_function=convert_work_packages,
                validation_model=WorkPackage,
                id_field="id",
            )

    async def unapply(self):
        """Revert the migration."""

        # define the change function
        async def revert_work_packages(doc: Document) -> Document:
            """Convert the fields back into strings"""
            doc["_id"] = str(doc["_id"])
            doc["user_id"] = str(doc["user_id"])
            for field in ["created", "expires"]:
                doc[field] = doc[field].isoformat()
            return doc

        async with self.auto_finalize(coll_names=[WORK_PACKAGES], copy_indexes=True):
            # Don't provide validation models here
            await self.migrate_docs_in_collection(
                coll_name=WORK_PACKAGES,
                change_function=revert_work_packages,
            )
