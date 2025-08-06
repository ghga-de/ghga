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
#

"""Mock implementation of the access check adapter."""

from datetime import timedelta
from uuid import UUID

from ghga_service_commons.utils.utc_dates import UTCDatetime, now_as_utc

from wps.ports.outbound.access import AccessCheckPort

USERS_WITH_DOWNLOAD_ACCESS = [UUID("a86f8281-e18a-429e-88a9-a5c8ea0cf754")]
DATASETS_WITH_DOWNLOAD_ACCESS = ["some-dataset-id"]

__all__ = ["AccessCheckMock"]


class AccessCheckMock(AccessCheckPort):
    """Mock checking dataset access permissions."""

    validity_period = timedelta(days=365)

    async def check_download_access(
        self, user_id: UUID, dataset_id: str
    ) -> UTCDatetime | None:
        """Check whether the given user has download access for the given dataset."""
        if (
            user_id not in USERS_WITH_DOWNLOAD_ACCESS
            or dataset_id not in DATASETS_WITH_DOWNLOAD_ACCESS
        ):
            return None
        return now_as_utc() + self.validity_period

    async def get_accessible_datasets_with_expiration(
        self, user_id: UUID
    ) -> dict[str, UTCDatetime]:
        """Get all datasets that the given user is allowed to download."""
        if user_id not in USERS_WITH_DOWNLOAD_ACCESS:
            return {}
        expires = now_as_utc() + self.validity_period
        return {
            dataset_id: expires
            for dataset_id in DATASETS_WITH_DOWNLOAD_ACCESS
            if dataset_id in DATASETS_WITH_DOWNLOAD_ACCESS
        }
