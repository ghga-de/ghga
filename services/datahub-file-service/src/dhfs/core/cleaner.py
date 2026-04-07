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

"""Post-interrogation S3 bucket cleanup logic"""

import logging

from dhfs.config import Config
from dhfs.ports.outbound.central import CentralClientPort
from dhfs.ports.outbound.cleaner import S3CleanerPort
from dhfs.ports.outbound.s3 import S3ClientPort

log = logging.getLogger(__name__)

__all__ = ["S3Cleaner"]


class S3Cleaner(S3CleanerPort):
    """Performs cleanup for the interrogation bucket"""

    def __init__(
        self,
        *,
        config: Config,
        central_client: CentralClientPort,
        s3_client: S3ClientPort,
    ):
        self._central_client = central_client
        self._s3_client = s3_client
        self._interrogation_storage_alias = config.interrogation_bucket_id

    async def scan_and_clean(self):
        """Get a list of all objects in the 'interrogation' bucket, then query the
        GHGA Central API and delete the objects which that API says may be deleted.

        Raises:
        - S3CleanupError if some objects can't be deleted from the interrogation bucket.

        Can also raise underlying errors from the S3 client or the CentralClient.
        """
        log.info("Starting interrogation bucket cleanup scan.")

        # TODO: Incomplete MPU cleanup - hexkit currently lacks a 'list ongoing MPUs' method
        try:
            object_ids = await self._s3_client.list_files_in_interrogation_bucket()
        except Exception as exc:
            log.error(
                "Failed to list files in interrogation bucket: %s.",
                exc,
                exc_info=True,
            )
            raise

        if not object_ids:
            log.info("No files to clean up, exiting.")
            return

        # No need to convert obj IDs to UUID here because they are serialized to string
        #  in the outbound request, and S3 expects strings. In short, we don't need the
        #  UUID properties, even for validation.
        try:
            removable_objects = await self._central_client.get_removable_files(
                object_ids=object_ids
            )
        except Exception as exc:
            log.error(
                "Failed to fetch removable files from Central API: %s.",
                exc,
                exc_info=True,
            )
            raise

        log.info(
            "Central API indicates %d file(s) can be removed.", len(removable_objects)
        )

        if not removable_objects:
            log.info("No files marked for removal, exiting.")
            return

        # Track deletion results
        deleted_count = 0
        failed_deletions = []

        for object_id in removable_objects:
            try:
                await self._s3_client.remove_file(object_id=object_id)
            except Exception as exc:
                log.error(
                    "Failed to delete file %s: %s",
                    object_id,
                    exc,
                    exc_info=True,
                )
                failed_deletions.append(object_id)
            else:
                deleted_count += 1
                log.debug("Successfully deleted file: %s", object_id)

        log.info(
            "Cleanup complete: %d file(s) deleted successfully, %d failed.",
            deleted_count,
            len(failed_deletions),
        )

        if failed_deletions:
            log.warning("Failed to delete the following files: %s", failed_deletions)
            raise self.S3CleanupError(failed_deletion_count=len(failed_deletions))
