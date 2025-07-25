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

"""Database migration logic for NOS"""

from ghga_event_schemas.pydantic_ import AccessRequestDetails, User
from hexkit.providers.mongodb.migrations import (
    Document,
    MigrationDefinition,
    Reversible,
)
from hexkit.providers.mongodb.migrations.helpers import convert_uuids_and_datetimes_v6


class V2Migration(MigrationDefinition, Reversible):
    """Update the stored data to have native-typed UUIDs and datetimes.

    This includes the User data and Access Request data.
    This can be reversed by converting the UUIDs and datetimes back to strings.
    """

    version = 2

    async def apply(self):
        """Perform the migration."""
        convert_access_requests = convert_uuids_and_datetimes_v6(
            uuid_fields=["_id", "user_id"], date_fields=["access_starts", "access_ends"]
        )

        convert_users = convert_uuids_and_datetimes_v6(uuid_fields=["_id"])

        async with self.auto_finalize(
            coll_names=["accessRequests", "users"], copy_indexes=True
        ):
            await self.migrate_docs_in_collection(
                coll_name="accessRequests",
                change_function=convert_access_requests,
                validation_model=AccessRequestDetails,
                id_field="id",
            )
            await self.migrate_docs_in_collection(
                coll_name="users",
                change_function=convert_users,
                validation_model=User,
                id_field="user_id",
            )

    async def unapply(self):
        """Revert the migration."""

        async def revert_access_requests(doc: Document) -> Document:
            """Convert Access Request documents back to string UUIDs and isoformat datetimes."""
            for field in ["_id", "user_id"]:
                doc[field] = str(doc[field])
            for field in ["access_starts", "access_ends"]:
                doc[field] = doc[field].isoformat()
            return doc

        async def revert_users(doc: Document) -> Document:
            """Convert User documents back to string UUIDs."""
            doc["_id"] = str(doc["_id"])
            return doc

        async with self.auto_finalize(
            coll_names=["accessRequests", "users"], copy_indexes=True
        ):
            # Don't provide validation models here
            await self.migrate_docs_in_collection(
                coll_name="accessRequests",
                change_function=revert_access_requests,
            )
            await self.migrate_docs_in_collection(
                coll_name="users",
                change_function=revert_users,
            )
