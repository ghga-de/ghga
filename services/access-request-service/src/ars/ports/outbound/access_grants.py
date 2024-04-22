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

"""Outbound access grants"""

from abc import ABC, abstractmethod

from ghga_service_commons.utils.utc_dates import UTCDatetime

__all__ = ["AccessGrantsPort"]


class AccessGrantsPort(ABC):
    """A port for granting download access permissions for datasets."""

    class AccessGrantsError(RuntimeError):
        """Raised when there was an error in storing the access grant."""

    class AccessGrantsInvalidPeriodError(AccessGrantsError):
        """Raised when there was an error in the validity period."""

    @abstractmethod
    async def grant_download_access(  # noqa: PLR0913
        self,
        user_id: str,
        iva_id: str,
        dataset_id: str,
        valid_from: UTCDatetime,
        valid_until: UTCDatetime,
    ) -> None:
        """Grant download access to a given user with an IVA for a given dataset."""
        ...
