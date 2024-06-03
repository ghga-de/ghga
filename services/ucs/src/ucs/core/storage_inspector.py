# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
#
"""Functionality to periodically deal with stale files in configured object storage."""

import logging

from ghga_service_commons.utils.multinode_storage import (
    S3ObjectStorages,
    S3ObjectStoragesConfig,
)
from hexkit.protocols.dao import MultipleHitsFoundError, NoHitsFoundError

from ucs.core.models import UploadStatus
from ucs.ports.inbound.storage_inspector import StorageInspectorPort
from ucs.ports.inbound.upload_service import UploadServicePort
from ucs.ports.outbound.dao import DaoCollectionPort

log = logging.getLogger(__name__)


class InboxInspector(StorageInspectorPort):
    """Checks inbox storage buckets for stale files."""

    def __init__(
        self,
        config: S3ObjectStoragesConfig,
        daos: DaoCollectionPort,
        object_storages: S3ObjectStorages,
    ):
        """Initialize with DB DAOs and storage handles."""
        self._config = config
        self._daos = daos
        self._object_storages = object_storages

    async def check_buckets(self):
        """Check objects in all buckets configured for the service."""
        for storage_alias in self._config.object_storages:
            log.debug("Checking for stale objects in storage '%s'", storage_alias)

            bucket_id, object_storage = self._object_storages.for_alias(
                endpoint_alias=storage_alias
            )
            object_ids = await object_storage.list_all_object_ids(bucket_id=bucket_id)

            for object_id in object_ids:
                try:
                    attempt = await self._daos.upload_attempts.find_one(
                        mapping={"object_id": object_id}
                    )
                except (MultipleHitsFoundError, NoHitsFoundError) as error:
                    # This service checks for inconsistencies elsewhere, so also check here
                    out_of_sync = UploadServicePort.StorageAndDatabaseOutOfSyncError(
                        problem=f"Unexpected amount of hits in database for object {object_id}"
                        + f" in storage identified by alias {storage_alias}."
                    )
                    log.critical(
                        out_of_sync,
                        extra={"object_id": object_id, "storage_alias": storage_alias},
                    )
                    raise out_of_sync from error

                # check if associated attempt status is one of the final statuses
                if attempt.status in [
                    UploadStatus.ACCEPTED,
                    UploadStatus.CANCELLED,
                    UploadStatus.FAILED,
                    UploadStatus.REJECTED,
                ]:
                    extra = {
                        "object_id": object_id,
                        "file_id": attempt.file_id,
                        "bucket_id": bucket_id,
                        "storage_alias": storage_alias,
                    }
                    # only log for now, but this points to an underlying issue
                    log.error(
                        "Stale object '%s' found for file '%s' in bucket '%s' of storage '%s'.",
                        *extra.values(),
                        extra=extra,
                    )
