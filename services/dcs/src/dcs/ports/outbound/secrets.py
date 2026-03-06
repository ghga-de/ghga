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

"""Port definition for a class that calls the Secrets API"""

from abc import ABC, abstractmethod


class SecretsClientPort(ABC):
    """A class to communicate with the Secrets API regarding file encryption secrets"""

    @abstractmethod
    async def get_envelope(self, *, secret_id: str, receiver_public_key: str) -> str:
        """Call the Secrets API to get an envelope for an encrypted file, using the
        receiver's public key as well as the id of the file secret.

        Raises:
            RequestFailedError: if an error prevents obtaining a response.
            BadResponseCodeError: if a response is received but the status code
                indicates that the request was unsuccessful.
        """

    @abstractmethod
    async def delete_secret(self, *, secret_id: str) -> None:
        """Call the Secrets API to delete a file secret

        Raises:
            RequestFailedError: if an error prevents obtaining a response.
            BadResponseCodeError: if a response is received but the status code
                indicates that the request was unsuccessful.
        """
