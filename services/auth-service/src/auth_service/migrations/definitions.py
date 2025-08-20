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

"""Database migration logic for Auth Service"""

from datetime import UTC, datetime
from uuid import UUID

from hexkit.providers.mongodb.migrations import (
    Document,
    MigrationDefinition,
    Reversible,
)
from hexkit.providers.mongodb.migrations.helpers import convert_uuids_and_datetimes_v6
from hexkit.utils import round_datetime_to_ms

from auth_service.config import Config


class V2Migration(MigrationDefinition, Reversible):
    """Update the stored data to have native-typed UUIDs and datetimes and switch
    to new event structure:

    There are 4 collections to modify:
    - claims:
      - *iva_id
      - valid_from
      - valid_until
      - id (_id)
      - user_id
      - *revocation_date
      - creation_date
      - assertion_date

    - ivas:
      - id (_id)
      - user_id
      - created
      - changed
      - __metadata__.correlation_id

    - user tokens:
      - user_id (_id)

    - users:
      - id (_id)
      - registration_date
      - *by
      - *change_date
      - __metadata__.correlation_id

    * = optional fields that might contain null values in the DB.
    """

    version = 2

    async def apply(self):  # noqa: C901
        """Perform the migration."""
        config = Config()  # type: ignore
        all_collections = [
            config.claims_collection,
            config.ivas_collection,
            config.user_tokens_collection,
            config.users_collection,
        ]

        def _convert_fields(
            *,
            doc: Document,
            uuid_fields: list[str] | None = None,
            date_fields: list[str] | None = None,
        ) -> Document:
            """Convert fields, skipping nulls."""
            for uuid_field in uuid_fields or []:
                if doc_value := doc.get(uuid_field):
                    doc[uuid_field] = UUID(doc_value)

            for date_field in date_fields or []:
                if doc_value := doc.get(date_field):
                    old_dt = datetime.fromisoformat(doc_value)
                    if old_dt.tzname() != "UTC":
                        old_dt = old_dt.astimezone(UTC)
                    doc[date_field] = round_datetime_to_ms(old_dt)
            return doc

        async def _convert_claim(doc: Document) -> Document:
            """Convert a claims doc"""
            doc = _convert_fields(
                doc=doc,
                uuid_fields=["_id", "iva_id", "user_id"],
                date_fields=[
                    "valid_from",
                    "valid_until",
                    "creation_date",
                    "assertion_date",
                    "revocation_date",
                ],
            )
            return doc

        _convert_core_iva_fields = convert_uuids_and_datetimes_v6(
            uuid_fields=["user_id"],
            date_fields=["created", "changed"],
        )

        async def _convert_iva(doc: Document) -> Document:
            """Convert an IVA doc"""
            doc["_id"] = UUID(doc["_id"])

            metadata = doc.get("__metadata__", {})
            if cid := metadata.get("correlation_id"):
                doc["__metadata__"]["correlation_id"] = UUID(cid)
            if not metadata["deleted"]:
                # deleted outbox docs only have the _id field and metadata
                doc = await _convert_core_iva_fields(doc)
            return doc

        _convert_user_reg_date = convert_uuids_and_datetimes_v6(
            date_fields=["registration_date"]
        )

        async def _convert_user(doc: Document) -> Document:
            """Convert a user doc"""
            doc["_id"] = UUID(doc["_id"])

            metadata = doc.get("__metadata__", {})
            if cid := metadata.get("correlation_id"):
                doc["__metadata__"]["correlation_id"] = UUID(cid)
            if not metadata["deleted"]:
                # deleted outbox docs only have the _id field and metadata
                doc = await _convert_user_reg_date(doc)
                if status_change := doc.get("status_change"):
                    doc["status_change"] = _convert_fields(
                        doc=status_change,
                        uuid_fields=["by"],
                        date_fields=["change_date"],
                    )
            return doc

        async with self.auto_finalize(coll_names=all_collections, copy_indexes=True):
            # Migrate claims
            await self.migrate_docs_in_collection(
                coll_name=config.claims_collection,
                change_function=_convert_claim,
            )

            # Migrate IVAs (all fields are required)
            await self.migrate_docs_in_collection(
                coll_name=config.ivas_collection,
                change_function=_convert_iva,
            )

            # Migrate user tokens (only one field to change, and it is required)
            await self.migrate_docs_in_collection(
                coll_name=config.user_tokens_collection,
                change_function=convert_uuids_and_datetimes_v6(uuid_fields=["_id"]),
            )

            # Migrate users (some optional fields, but they are nested)
            await self.migrate_docs_in_collection(
                coll_name=config.users_collection,
                change_function=_convert_user,
            )

    async def unapply(self):  # noqa: C901
        """Reverse the migration."""
        config = Config()  # type: ignore
        all_collections = [
            config.claims_collection,
            config.ivas_collection,
            config.user_tokens_collection,
            config.users_collection,
        ]

        def _revert_fields(
            *,
            doc: Document,
            uuid_fields: list[str] | None = None,
            date_fields: list[str] | None = None,
        ) -> Document:
            """Revert fields, skipping nulls."""
            for uuid_field in uuid_fields or []:
                if doc_value := doc.get(uuid_field):
                    doc[uuid_field] = str(doc_value)

            for date_field in date_fields or []:
                if doc_value := doc.get(date_field):
                    doc[date_field] = doc_value.isoformat()
            return doc

        async def _revert_claim(doc: Document) -> Document:
            """Revert a claim doc"""
            return _revert_fields(
                doc=doc,
                uuid_fields=["_id", "iva_id", "user_id"],
                date_fields=[
                    "valid_from",
                    "valid_until",
                    "revocation_date",
                    "creation_date",
                    "assertion_date",
                ],
            )

        async def _revert_iva(doc: Document) -> Document:
            """Revert an iva doc"""
            doc = _revert_fields(
                doc=doc,
                uuid_fields=["_id", "user_id"],
                date_fields=["created", "changed"],
            )
            if cid := doc.get("__metadata__", {}).get("correlation_id"):
                doc["__metadata__"]["correlation_id"] = str(cid)
            return doc

        async def _revert_user_token(doc: Document) -> Document:
            """Revert a user token doc"""
            doc["_id"] = str(doc["_id"])
            return doc

        async def _revert_user(doc: Document) -> Document:
            """Revert a user doc"""
            if status_change := doc.get("status_change"):
                status_change = _revert_fields(
                    doc=status_change, uuid_fields=["by"], date_fields=["change_date"]
                )
                doc["status_change"] = status_change
            doc = _revert_fields(
                doc=doc, uuid_fields=["_id"], date_fields=["registration_date"]
            )
            if cid := doc.get("__metadata__", {}).get("correlation_id"):
                doc["__metadata__"]["correlation_id"] = str(cid)
            return doc

        async with self.auto_finalize(coll_names=all_collections, copy_indexes=True):
            # Revert claims
            await self.migrate_docs_in_collection(
                coll_name=config.claims_collection,
                change_function=_revert_claim,
            )

            # Revert IVAs
            await self.migrate_docs_in_collection(
                coll_name=config.ivas_collection,
                change_function=_revert_iva,
            )

            # Revert user tokens
            await self.migrate_docs_in_collection(
                coll_name=config.user_tokens_collection,
                change_function=_revert_user_token,
            )

            # Revert users
            await self.migrate_docs_in_collection(
                coll_name=config.users_collection,
                change_function=_revert_user,
            )
