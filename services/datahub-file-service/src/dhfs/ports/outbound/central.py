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

"""Interface definition of a class that communicates with GHGA Central"""

from abc import ABC, abstractmethod

from dhfs.core.models import FileUpload, InterrogationReport

__all__ = ["CentralClientPort"]


class CentralClientPort(ABC):
    """This class communicates with GHGA Central to learn about new file uploads"""

    class ResponseFormatError(RuntimeError):
        """Raised when an otherwise valid response has an unexpected body format"""

        def __init__(self, url: str):
            msg = (
                f"Tried to fetch new File Uploads from {url} but couldn't"
                + " parse the response."
            )
            super().__init__(msg)

    class UpgradeRequiredError(RuntimeError):
        """Raised when GHGA Central claims this DHFS instance is outdated"""

        def __init__(self) -> None:
            msg = (
                "The GHGA Central API has rejected this request (HTTP 426): this DHFS"
                + " installation is outdated. Please upgrade DHFS by following GHGA's"
                + " upgrade documentation."
            )
            super().__init__(msg)

    class CentralAPIError(RuntimeError):
        """Raised when something goes wrong with a call to the Central API"""

        def __init__(self, *, url: str, status_code: int):
            msg = f"The call to {url} failed with a status code of {status_code}."
            super().__init__(msg)

    @abstractmethod
    async def fetch_new_uploads(self) -> list[FileUpload]:
        """Fetch a list of files that need to be interrogated and re-encrypted.

        Raises:
        - CentralAPIError if the request to the central API fails.
        - UpgradeRequiredError if the central API indicates this DHFS instance is outdated
        - ResponseFormatError if response body parsing fails.
        """
        ...

    @abstractmethod
    async def get_removable_files(self, *, object_ids: list[str]) -> list[str]:
        """Ask the GHGA Central API if the objects corresponding to the given object IDs
        can be removed from `interrogation` bucket.

        Returns a list of object IDs that may be removed from the bucket.

        Raises:
        - CentralAPIError if the request to the central API fails.
        """
        ...

    @abstractmethod
    async def submit_interrogation_report(self, *, report: InterrogationReport) -> None:
        """Submit a file interrogation report to GHGA Central

        Raises:
        - CentralAPIError if the request to the central API fails.
        """
        ...
