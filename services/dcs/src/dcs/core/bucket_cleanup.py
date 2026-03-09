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

"""Download bucket cleanup logic."""

import logging
import uuid
from datetime import timedelta

from ghga_service_commons.utils.multinode_storage import (
    S3ObjectStorages,
    S3ObjectStoragesConfig,
)
from hexkit.protocols.dao import NoHitsFoundError
from hexkit.utils import now_utc_ms_prec
from pydantic import Field
from pydantic_settings import BaseSettings

from dcs.core.errors import StorageAliasNotConfiguredError
from dcs.ports.inbound.bucket_cleanup import BucketCleanerPort
from dcs.ports.outbound.dao import DrsObjectDaoPort

log = logging.getLogger(__name__)


class BucketCleanupConfig(BaseSettings):
    """Config parameters needed for the DownloadBucketCleaner."""

    download_bucket_cache_timeout: int = Field(
        default=7,
        description="Time in days since last access after which a file present in the "
        + "download bucket should be unstaged and has to be requested from "
        + "permanent storage again for the next request.",
        examples=[7, 30],
    )


class DownloadBucketCleaner(BucketCleanerPort):
    """A service that manages download bucket cleanup."""

    def __init__(
        self,
        *,
        config: BucketCleanupConfig,
        drs_object_dao: DrsObjectDaoPort,
        object_storages: S3ObjectStorages,
    ):
        """Initialize with essential config params and outbound adapters."""
        self._config = config
        self._drs_object_dao = drs_object_dao
        self._object_storages = object_storages

    async def cleanup_download_buckets(
        self,
        *,
        object_storages_config: S3ObjectStoragesConfig,
        remove_dangling_objects: bool = False,
    ):
        """Run cleanup task for all download buckets configured in the service config."""
        for storage_alias in object_storages_config.object_storages:
            await self.cleanup_download_bucket(
                storage_alias=storage_alias,
                remove_dangling_objects=remove_dangling_objects,
            )

    async def cleanup_download_bucket(
        self, *, storage_alias: str, remove_dangling_objects: bool = False
    ):
        """
        Check if files present in the download bucket have outlived their allocated time
        and remove all that do.
        For each file in the download bucket, its 'last_accessed' field is checked and compared
        to the current datetime. If the threshold configured in the download_bucket_cache_timeout
        option is met or exceeded, the corresponding file is removed from the download bucket.
        """
        # Run on demand through CLI, so crashing should be ok if the alias is not configured
        log.info(
            "Starting download bucket cleanup for storage identified by alias %s.",
            storage_alias,
        )
        try:
            bucket_id, object_storage = self._object_storages.for_alias(storage_alias)
        except KeyError:
            storage_alias_not_configured = StorageAliasNotConfiguredError(
                alias=storage_alias
            )
            log.critical(storage_alias_not_configured)
            log.info(
                "Skipping download bucket cleanup for storage %s as it is not configured.",
                storage_alias,
            )
            return

        threshold = now_utc_ms_prec() - timedelta(
            days=self._config.download_bucket_cache_timeout
        )

        # filter to get all files in download bucket that should be removed
        object_ids = [
            uuid.UUID(x)
            for x in await object_storage.list_all_object_ids(bucket_id=bucket_id)
        ]
        log.debug(
            f"Retrieved list of deletion candidates for storage '{storage_alias}'"
        )

        for object_id in object_ids:
            force_removal = False
            try:
                drs_object = await self._drs_object_dao.find_one(
                    mapping={"object_id": object_id}
                )
            except NoHitsFoundError:
                if not remove_dangling_objects:
                    cleanup_error = self.CleanupError(
                        object_id=object_id,
                        storage_alias=storage_alias,
                        reason="Object not found in database, skipping.",
                    )
                    log.warning(cleanup_error)
                    continue
                force_removal = True

            # only remove file if last access is later than download bucket_cache_timeout days ago
            if force_removal or drs_object.last_accessed <= threshold:
                log.info(
                    "Deleting object %s from download bucket %s in storage %s.",
                    object_id,
                    bucket_id,
                    storage_alias,
                )
                try:
                    await object_storage.delete_object(
                        bucket_id=bucket_id, object_id=str(object_id)
                    )
                except (
                    object_storage.ObjectError,
                    object_storage.ObjectStorageProtocolError,
                ) as error:
                    cleanup_error = self.CleanupError(
                        object_id=object_id,
                        storage_alias=storage_alias,
                        reason=str(error),
                    )
                    log.error(cleanup_error)
