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

"""Interface for download bucket cleanup."""

from abc import ABC, abstractmethod

from ghga_service_commons.utils.multinode_storage import S3ObjectStoragesConfig
from pydantic import UUID4


class BucketCleanerPort(ABC):
    """A service that manages download bucket cleanup."""

    class CleanupError(RuntimeError):
        """
        Raised when removal of an object from the download bucket could not be performed
        due to an underlying issue
        """

        def __init__(self, *, object_id: UUID4, storage_alias: str, reason: str):
            message = f"Could not remove object {object_id} from download bucket in storage {storage_alias}: {reason}"
            super().__init__(message)

    @abstractmethod
    async def cleanup_download_buckets(
        self,
        *,
        object_storages_config: S3ObjectStoragesConfig,
        remove_dangling_objects: bool = False,
    ):
        """Run cleanup task for all download buckets configured in the service config."""

    @abstractmethod
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
