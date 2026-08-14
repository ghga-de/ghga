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

import asyncio
import logging

from dhfs.adapters.outbound.http import ConnectionFailedError
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
        self._max_concurrent_deletions = config.max_concurrent_deletions

    async def scan_and_clean(self):  # noqa: C901, PLR0911
        """Get a list of all objects in the 'interrogation' bucket, then query the
        GHGA Central API and delete the objects which that API says may be deleted.

        Raises:
        - S3CleanupError if some objects can't be deleted from the interrogation bucket.

        Can also raise underlying errors from the S3 client or the CentralClient.
        """
        # TODO: Finish MPU cleanup - hexkit now has the abilities needed
        try:
            object_ids = await self._s3_client.list_files_in_interrogation_bucket()
        except Exception as err:
            log.error(
                "Cleanup failed because DHFS couldn't get a list of the object IDs"
                + " currently residing in the interrogation bucket. Error text: %s",
                err,
            )
            return

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
        except ConnectionFailedError as err:
            log.error("Unable to reach the GHGA Central API (%s).", str(err))
            return
        except CentralClientPort.CentralAPIError as err:
            log.error("The GHGA Central API returned an error response: %s", err)
            return
        except CentralClientPort.ResponseFormatError as err:
            log.error(
                "The GHGA Central API returned an unrecognized response format: %s", err
            )
            return
        except Exception as err:
            log.error("Failed to determine which objects can be removed: %s", err)
            return

        if not removable_objects:
            log.info("No files marked for removal, exiting.")
            return

        failed_deletions: list[str] = []

        # Independent round trips; run a bounded number of them at once.
        semaphore = asyncio.Semaphore(self._max_concurrent_deletions)

        async def _remove(object_id: str) -> None:
            """Delete one object, recording a failure rather than raising it."""
            async with semaphore:
                try:
                    await self._s3_client.remove_file(object_id=object_id)
                except Exception:
                    failed_deletions.append(object_id)

        async with asyncio.TaskGroup() as task_group:
            for object_id in removable_objects:
                task_group.create_task(_remove(object_id))

        log.info(
            "Cleanup completed%s: %d file(s) deleted successfully, %d failed.",
            " with errors" if failed_deletions else "",
            len(removable_objects) - len(failed_deletions),
            len(failed_deletions),
            extra=(
                {"objects_unable_to_delete": failed_deletions}
                if failed_deletions
                else {}
            ),
        )
