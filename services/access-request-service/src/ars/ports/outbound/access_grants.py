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

"""Outbound access grants"""

from abc import ABC, abstractmethod

from ghga_service_commons.utils.utc_dates import UTCDatetime

from ars.core.models import BaseAccessGrant

__all__ = ["AccessGrantsPort"]


class AccessGrantsPort(ABC):
    """A port for checking and granting access permissions for datasets."""

    class AccessGrantsError(RuntimeError):
        """Raised when there was an error in storing the access grant."""

    class AccessGrantsInvalidPeriodError(AccessGrantsError):
        """Raised when there was an error in the validity period."""

    class AccessGrantNotFoundError(AccessGrantsError):
        """Raised when an expected access grant could not be found."""

    @abstractmethod
    async def grant_download_access(
        self,
        user_id: str,
        iva_id: str,
        dataset_id: str,
        valid_from: UTCDatetime,
        valid_until: UTCDatetime,
    ) -> None:
        """Grant download access to a given user with an IVA for a given dataset.

        May raise an `AccessGrantsInvalidPeriodError` or a general `AccessGrantsError`.
        """
        ...

    @abstractmethod
    async def get_download_access_grants(
        self,
        user_id: str | None = None,
        iva_id: str | None = None,
        dataset_id: str | None = None,
        valid: bool | None = None,
    ) -> list[BaseAccessGrant]:
        """Get download access grants.

        You can filter the grants by user ID, IVA ID, dataset ID and whether the grant
        is currently valid or not.

        May raise an `AccessGrantsError`.
        """
        ...

    @abstractmethod
    async def revoke_download_access_grant(self, grant_id: str) -> None:
        """Revoke a download access grant.

        May raise an `AccessGrantNotFoundError` or a general `AccessGrantsError`.
        """
        ...
