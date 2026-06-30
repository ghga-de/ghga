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

"""Port definition for a class that performs post-interrogation S3 bucket cleanup"""

from abc import ABC, abstractmethod

__all__ = ["S3CleanerPort"]


class S3CleanerPort(ABC):
    """A class that performs post-interrogation S3 bucket cleanup"""

    @abstractmethod
    async def scan_and_clean(self):
        """Get a list of all objects in the 'interrogation' bucket, then query the
        GHGA Central API and delete the objects which that API says may be deleted.

        Raises:
        - S3CleanupError if some objects can't be deleted from the interrogation bucket.

        Can also raise underlying errors from the S3 client or the CentralClient.
        """
        ...
