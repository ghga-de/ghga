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

"""DAO translators for accessing the database."""

from ghga_event_schemas.configs import FileUploadBoxEventsConfig, FileUploadEventsConfig
from hexkit.protocols.dao import DaoFactoryProtocol
from hexkit.protocols.daopub import DaoPublisher, DaoPublisherFactoryProtocol
from hexkit.providers.mongodb import MongoDbIndex

from ucs.constants import (
    FILE_UPLOAD_BOXES_COLLECTION,
    FILE_UPLOADS_COLLECTION,
    UPLOAD_ACTIVITY_COLLECTION,
)
from ucs.core.models import FileUpload, FileUploadBox, UploadActivity
from ucs.ports.outbound.dao import UploadActivityDao, UploadDaoPublisherFactoryPort

# The following FileUpload fields are UCS-only and excluded from outbox events
FIELDS_NOT_PUBLISHED: set[str] = {
    "inbox_upload_completed",
    "s3_upload_id",
    "initiated",
    "completed",
}


class UploadDaoConfig(FileUploadBoxEventsConfig, FileUploadEventsConfig):
    """Topic configuration for the published DTOs"""


class UploadDaoPublisherFactory(UploadDaoPublisherFactoryPort):
    """Translation between UploadDaoPublisherFactoryPort and DaoPublisherFactoryProtocol."""

    def __init__(
        self,
        *,
        config: UploadDaoConfig,
        dao_publisher_factory: DaoPublisherFactoryProtocol,
    ):
        self._file_upload_box_topic = config.file_upload_box_topic
        self._file_upload_topic = config.file_upload_topic
        self._dao_publisher_factory = dao_publisher_factory

    async def get_file_upload_box_dao(self) -> DaoPublisher[FileUploadBox]:
        """Construct an outbox DAO for FileUploadBox objects"""
        return await self._dao_publisher_factory.get_dao(
            name=FILE_UPLOAD_BOXES_COLLECTION,
            id_field="id",
            dto_model=FileUploadBox,
            dto_to_event=lambda x: x.model_dump(),
            event_topic=self._file_upload_box_topic,
            autopublish=True,
        )

    async def get_file_upload_dao(self) -> DaoPublisher[FileUpload]:
        """Construct an outbox DAO for FileUpload objects.

        The events published **do not** include the field `inbox_upload_completed`.
        """
        return await self._dao_publisher_factory.get_dao(
            name=FILE_UPLOADS_COLLECTION,
            id_field="id",
            dto_model=FileUpload,
            dto_to_event=lambda x: x.model_dump(exclude=FIELDS_NOT_PUBLISHED),
            event_topic=self._file_upload_topic,
            autopublish=True,
            indexes=[
                MongoDbIndex(
                    fields={"box_id": 1, "alias": 1},
                    properties={"unique": True, "sparse": True},
                ),
                # Supports the stale upload cleanup job, which queries by
                #  storage_alias and state
                MongoDbIndex(fields={"storage_alias": 1, "state": 1}),
                # Covering index for the box stats aggregation: matching on
                #  box_id + state and summing decrypted_size can be served entirely
                #  from this index without fetching documents
                MongoDbIndex(fields={"box_id": 1, "state": 1, "decrypted_size": 1}),
            ],
        )


async def get_upload_activity_dao(
    *, dao_factory: DaoFactoryProtocol
) -> UploadActivityDao:
    """Get an UploadActivityDao for UploadActivity objects."""
    return await dao_factory.get_dao(
        name=UPLOAD_ACTIVITY_COLLECTION,
        id_field="file_id",
        dto_model=UploadActivity,
    )
