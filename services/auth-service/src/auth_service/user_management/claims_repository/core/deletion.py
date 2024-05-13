# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Handler for the deletion of access permissions."""

import logging

from ..deps import ClaimDao
from ..ports.deletion import DatasetDeletionPort
from .claims import create_controlled_access_filter

log = logging.getLogger(__name__)


class DatasetDeletionHandler(DatasetDeletionPort):
    """Handler for dataset deletions."""

    def __init__(self, *, claim_dao: ClaimDao):
        """Initialize the handler with the DAO for claims."""
        self.claim_dao = claim_dao

    async def handle_dataset_deletion(self, *, dataset_id: str) -> None:
        """Delete all access rights for datasets with the given id."""
        claims_filter = create_controlled_access_filter(dataset_id)
        count_deleted = 0
        async for dataset in self.claim_dao.find_all(mapping=claims_filter):
            await self.claim_dao.delete(dataset.id)
            count_deleted += 1
        log.info("Deleted %d claims for dataset %s", count_deleted, dataset_id)
