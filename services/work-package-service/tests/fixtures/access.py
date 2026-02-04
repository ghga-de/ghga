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
#

"""Mock implementation of the access check adapter."""

from datetime import timedelta
from uuid import UUID

from ghga_service_commons.utils.utc_dates import UTCDatetime
from hexkit.utils import now_utc_ms_prec
from pydantic import UUID4

from wps.ports.outbound.access import AccessCheckPort

USERS_WITH_DOWNLOAD_ACCESS = [UUID("a86f8281-e18a-429e-88a9-a5c8ea0cf754")]
USERS_WITH_UPLOAD_ACCESS = [UUID("4624fb56-2d5f-4a8a-9a6c-cc0226a4f55a")]
DATASETS_WITH_DOWNLOAD_ACCESS = ["some-dataset-id"]
BOXES_WITH_UPLOAD_ACCESS = [
    UUID("e47f4b8a-3f2c-4e8b-9a1c-7d4e5f6a7b8c"),
    UUID("f58e5c9b-4e3d-4f9c-ab2d-8e5f6a7b8c9d"),
]
USER_FOR_ACCESS_CHECK_ERROR = UUID("144ae997-2edd-45b7-a9b1-7ea8c1c73c69")

__all__ = ["AccessCheckMock"]


class AccessCheckMock(AccessCheckPort):
    """Mock checking dataset access permissions."""

    validity_period = timedelta(days=365)

    async def check_download_access(
        self, user_id: UUID, dataset_id: str
    ) -> UTCDatetime | None:
        """Check whether the given user has download access for the given dataset."""
        if user_id == USER_FOR_ACCESS_CHECK_ERROR:
            raise AccessCheckPort.AccessCheckError("Simulated access check error")
        if (
            user_id not in USERS_WITH_DOWNLOAD_ACCESS
            or dataset_id not in DATASETS_WITH_DOWNLOAD_ACCESS
        ):
            return None
        return now_utc_ms_prec() + self.validity_period

    async def get_accessible_datasets_with_expiration(
        self, user_id: UUID
    ) -> dict[str, UTCDatetime]:
        """Get all datasets that the given user is allowed to download."""
        if user_id == USER_FOR_ACCESS_CHECK_ERROR:
            raise AccessCheckPort.AccessCheckError("Simulated access check error")
        if user_id not in USERS_WITH_DOWNLOAD_ACCESS:
            return {}
        expires = now_utc_ms_prec() + self.validity_period
        return {
            dataset_id: expires
            for dataset_id in DATASETS_WITH_DOWNLOAD_ACCESS
            if dataset_id in DATASETS_WITH_DOWNLOAD_ACCESS
        }

    async def check_upload_access(
        self, user_id: UUID, box_id: UUID
    ) -> UTCDatetime | None:
        """Check whether the given user has upload access for the given box."""
        if user_id == USER_FOR_ACCESS_CHECK_ERROR:
            raise AccessCheckPort.AccessCheckError("Simulated access check error")
        if (
            user_id not in USERS_WITH_UPLOAD_ACCESS
            or box_id not in BOXES_WITH_UPLOAD_ACCESS
        ):
            return None
        return now_utc_ms_prec() + self.validity_period

    async def get_accessible_boxes_with_expiration(
        self, user_id: UUID
    ) -> dict[UUID4, UTCDatetime]:
        """Get all upload boxes that the given user is allowed to upload to."""
        if user_id == USER_FOR_ACCESS_CHECK_ERROR:
            raise AccessCheckPort.AccessCheckError("Simulated access check error")
        if user_id not in USERS_WITH_UPLOAD_ACCESS:
            return {}
        expires = now_utc_ms_prec() + self.validity_period
        return {box_id: expires for box_id in BOXES_WITH_UPLOAD_ACCESS}
